"""
/speedtest{suffix} — per-client Telegram throughput diagnostic.

Sends a synthetic in-memory upload (RAM-only, no disk I/O) through each
available Telegram client (main bot + user session + every helper bot &
helper user) and reports per-client MB/s. Lets you spot a silently
degraded helper, a non-Premium user-session cap, or pure-python pyaes
fallback (everything <= ~2 MB/s = crypto fallback or token throttle).
"""

import asyncio
import io
import os
import time

from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..helper.ext_utils.bot_utils import new_task
from ..helper.telegram_helper.message_utils import edit_message, send_message


# 16 MB is enough to amortise the auth handshake + key-exchange latency
# while staying small enough to avoid actually triggering Telegram's
# throttle window (the throttle kicks in around ~50 MB sustained).
_TEST_SIZE_MB = 16
_TEST_SIZE = _TEST_SIZE_MB * 1024 * 1024


def _all_clients():
    """Yield (label, client) for every running pyrogram client."""
    if TgClient.bot is not None:
        yield "main-bot", TgClient.bot
    if TgClient.user is not None:
        label = "user-premium" if getattr(TgClient, "IS_PREMIUM_USER", False) else "user"
        yield label, TgClient.user
    for idx, hb in (getattr(TgClient, "helper_bots", None) or {}).items():
        yield f"helper-bot-{idx}", hb
    for idx, hu in (getattr(TgClient, "helper_users", None) or {}).items():
        yield f"helper-user-{idx}", hu


async def _bench_one(label, client, target_chat, payload_bytes):
    """Send `payload_bytes` once and measure wall-clock seconds + MB/s."""
    try:
        # Fresh BytesIO per client; Pyrogram consumes the stream.
        buf = io.BytesIO(payload_bytes)
        buf.name = f"speedtest-{label}.bin"
        t0 = time.monotonic()
        sent = await client.send_document(
            chat_id=target_chat,
            document=buf,
            file_name=f"speedtest-{label}.bin",
            disable_notification=True,
            force_document=True,
        )
        elapsed = time.monotonic() - t0
        # Clean up the test file in the dump chat right away
        try:
            await client.delete_messages(target_chat, sent.id)
        except Exception:
            pass
        mbps = (_TEST_SIZE / 1024 / 1024) / max(elapsed, 0.001)
        return label, mbps, elapsed, None
    except Exception as e:  # noqa: BLE001
        return label, 0.0, 0.0, f"{type(e).__name__}: {e}"


@new_task
async def speedtest(_, message):
    dump = Config.LEECH_DUMP_CHAT or getattr(Config, "LOG_CHAT_ID", None)
    try:
        dump = int(dump) if dump else None
    except (TypeError, ValueError):
        pass
    if not dump:
        await send_message(
            message,
            "<b>Speedtest needs <code>LEECH_DUMP_CHAT</code> (or "
            "<code>LOG_CHAT_ID</code>) so test uploads have a destination. "
            "Set one of these env vars and restart.</b>",
        )
        return

    status = await send_message(
        message,
        f"<b>📡 Running Telegram speed test...</b>\n"
        f"Uploading {_TEST_SIZE_MB} MB through each client in parallel.",
    )

    payload = os.urandom(_TEST_SIZE)

    clients = list(_all_clients())
    if not clients:
        await edit_message(status, "<b>No running pyrogram clients to test.</b>")
        return

    results = await asyncio.gather(
        *(_bench_one(label, c, dump, payload) for label, c in clients),
        return_exceptions=False,
    )

    lines = [f"<b>📡 Telegram per-client speed test ({_TEST_SIZE_MB} MB each)</b>", ""]
    ok_speeds = []
    for label, mbps, elapsed, err in results:
        if err:
            lines.append(f"<code>{label:<18}</code> ❌ {err}")
        else:
            badge = "🟢" if mbps >= 8 else "🟡" if mbps >= 3 else "🔴"
            lines.append(
                f"<code>{label:<18}</code> {badge} "
                f"{mbps:6.2f} MB/s  ({elapsed:.2f}s)"
            )
            ok_speeds.append(mbps)

    if ok_speeds:
        lines.append("")
        lines.append(f"<b>Sum (parallel)</b>  : <code>{sum(ok_speeds):6.2f}</code> MB/s")
        lines.append(f"<b>Best single</b>    : <code>{max(ok_speeds):6.2f}</code> MB/s")
        lines.append("")
        lines.append(
            "🟢 ≥ 8 MB/s   🟡 3–8 MB/s   🔴 &lt; 3 MB/s "
            "(red = throttle / pyaes / lost-admin)"
        )

    await edit_message(status, "\n".join(lines))
