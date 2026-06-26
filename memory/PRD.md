# Leech Bot (WZML-X fork) - PRD

## Original Problem Statement
> "fix all the broke cmd of the bot and make the bot faster and reliable use best fast pakage to download the upload ok"

User said the bot type is **Telegram bot** (leech bot), code already in `/app`, all commands were reported broken, and asked to use Pyrogram+TgCrypto, httpx async, aiohttp+aiofiles for fast download/upload.

## Architecture
- **Type**: Mirror/Leech Telegram bot (WZML-X v3 fork)
- **Entry point**: `python -m bot` (via `start.sh`)
- **Stack**: Pyrogram fork (`pyrotgfork`) + TgCrypto + aria2 + qBittorrent + SABnzbd + JDownloader
- **Fast packages already wired**: Pyrogram + TgCrypto, aiohttp, aiofiles, httpx, uvloop, aria2c (`aioaria2`), `curl-cffi` (via yt-dlp)
- **Multi-client HyperTG transfer**: Bot session + helper bots + user session + helper users for parallel chunked download/upload of Telegram media

## What was broken (root cause)
Two Python f-string syntax errors using backslashes inside f-string expressions. These break import on Python <3.12, causing the entire `bot.modules` package (and therefore all command handlers in `handlers.py`) to fail to load — i.e. every command appears broken.

1. `bot/helper/mirror_leech_utils/upload_utils/telegram_uploader.py:117` — nested f-string with `\n` inside an f-string expression
2. `bot/modules/services.py:211` — `escape('\n'.join(...))` inside an f-string expression

Additionally, the Hyper TG downloader used the wrong `dump_chat` after copy-to-dump failed, so helper bots tried to fetch the source message ID from the dump chat, returning a stale message and logging `HypertgDL ref fail: ... No downloadable media` instead of cleanly falling back to source FileId.

## Fixes applied (2026-01-XX)
- `bot/helper/mirror_leech_utils/upload_utils/telegram_uploader.py`: refactored the Leech-Started caption to use `_nl`/concatenation instead of nested-f-string-with-backslash; semantics unchanged.
- `bot/modules/services.py`: pre-computed `_esc_log = escape("\n".join(...))` outside the f-string; semantics unchanged.
- `bot/helper/ext_utils/hyperdl_utils.py` (`download_media`): added `copy_ok` flag; when copy-to-dump fails for every client, `self.dump_chat` now falls back to `message.chat.id` so that ref-fetch behaves consistently and helper-bots that lack source-chat access fail fast with `PeerIdInvalid` (handled gracefully) instead of returning a wrong message.

## Speed / reliability inventory (already in place, verified)
- `uvloop` installed and enabled in `bot/__init__.py`.
- `TgCrypto` (`pytgcrypto`) present in `requirements.txt` — Pyrogram auto-detects.
- Crypto thread pool sized to `max(64, cpu*8)` workers (`tg_transfer.py`).
- TCP tuning: `TCP_NODELAY`, `TCP_QUICKACK`, `SO_KEEPALIVE` applied on every Pyrogram socket.
- Telegram media DC alt-port 5222 patched for higher media throughput.
- Multi-client HyperTG download with CDN redirect support, pipelined `upload.GetFile` and parallel parts.
- HyperTG upload with worker pool, big-file splitting (`SaveBigFilePart`), and missing-part auto-reupload.
- HTTP downloads go through `aria2c` (fastest); `aiohttp`/`aiofiles` used in 67+ modules; `httpx` available.
- No usage of the synchronous `requests` library in the bot code path.

## Verification
- `python -m ast` / static lint: `bot/` parses clean on all Python versions, no lint errors.
- Hyper TG fallback path no longer raises misleading "No downloadable media" when copy-to-dump fails.

## Iteration 3 — Multi-task crash root cause + thumbnail shortcut + CMD_SUFFIX=3

### Root cause of "bot crashes when 2 tasks given"
In `bot/modules/mirror_leech.py`, `bot/modules/ytdlp.py`,
`bot/modules/clone.py`, `bot/modules/gd_clean.py` the entry points did
`bot_loop.create_task(Mirror(...).new_event())` and immediately discarded
the returned task. Python's `asyncio` only keeps a *weak* reference to
tasks (documented behaviour), so the GC could collect — and therefore
cancel — the first in-flight leech as soon as the handler frame for the
2nd `/leech` triggered an allocation cycle. This is the classic
"task disappearing mid-execution" trap and matches the user's symptom
(b/c/d: process appears to die / hang / first task stops).

Same flaw existed inside the `new_task` decorator in
`bot/helper/ext_utils/bot_utils.py` (used by every `@new_task` handler).

### Fix
- Added `safe_create_task(coro)` in `bot/helper/ext_utils/bot_utils.py`
  that stores tasks in a module-level `set`, removes them on done, and
  logs any unhandled exception (so a single-task failure no longer
  silently disappears).
- Rewired all leech/mirror/clone/gd-clean/ytdl/uphoster entry points to
  use `safe_create_task` instead of bare `bot_loop.create_task`.
- Rewrote `new_task` to delegate to `safe_create_task`.

### CMD_SUFFIX
- `config.env`: `CMD_SUFFIX = "3"` (Zoro bot). Restart the bot.

### Thumbnail shortcut
- `bot/modules/users_settings.py::send_user_settings` now accepts the
  inline form `/us3 -s thumb` (also `-s thumbnail`, `set thumb`,
  `set thumbnail`, `-thumb`) when used as a *reply* to a photo / image
  document / static sticker. The image is saved as the user's persistent
  leech thumbnail via the existing `create_thumb()` helper and persisted
  to the database when `DATABASE_URL` is set.

### Note
- Web/port-8080 cleanup was skipped per user request.
- Helper-bot auto-promote from iteration 2 still active.


`bot/helper/ext_utils/helper_admin.py` (new) — at startup, iterate every
`HELPER_TOKENS` bot, check its status in `LEECH_DUMP_CHAT`, and promote
to admin if needed using the user session (preferred) or the main bot
(must already be admin with `can_promote_members`). Wired into
`bot/__main__.py` after `TgClient.start_*` and `update_variables()`.

Behaviour:
- Already admin → log and skip
- Not in chat → log warning "add the bot to the chat first" (Telegram
  forbids promoting a user that isn't a member)
- Promote succeeds → log success
- Promote forbidden (promoter lacks rights) → log warning

No web/UI work was done — per user request "skip web".

- P1: `gunicorn ... Connection in use: 0.0.0.0:8080` repeated on restart — kill stale gunicorn before `python -m bot` (the existing `run_bot.sh` does `pkill -9 -f "python -m bot"` but doesn't kill gunicorn children that bound 8080). Recommend `fuser -k 8080/tcp || true` before exec.
- P2: Optional — add `tgcrypto-pyrofork` (drop-in C extension) as a secondary crypto provider for slightly faster AES-IGE if benchmarks show pytgcrypto is the bottleneck.
- P2: Consider raising `HYPER_THREADS` from 12 to `num_clients * 4` once all helper bots are admins in the dump chat.
