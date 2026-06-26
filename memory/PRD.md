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

## Backlog / Next actions
- P1: User must add each `HELPER_TOKENS` bot **as admin** to `LEECH_DUMP_CHAT` (`-1003864293232`) to unlock full multi-client Hyper TG speed. Without admin access helper bots can't fetch refs from the dump chat and the bot silently runs on fewer parallel clients.
- P1: `gunicorn ... Connection in use: 0.0.0.0:8080` repeated on restart — kill stale gunicorn before `python -m bot` (the existing `run_bot.sh` does `pkill -9 -f "python -m bot"` but doesn't kill gunicorn children that bound 8080). Recommend `fuser -k 8080/tcp || true` before exec.
- P2: Optional — add `tgcrypto-pyrofork` (drop-in C extension) as a secondary crypto provider for slightly faster AES-IGE if benchmarks show pytgcrypto is the bottleneck.
- P2: Consider raising `HYPER_THREADS` from 12 to `num_clients * 4` once all helper bots are admins in the dump chat.
