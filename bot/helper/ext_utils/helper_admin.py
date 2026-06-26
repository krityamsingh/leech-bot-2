"""Auto-promote helper bots to admin in LEECH_DUMP_CHAT.

Telegram requires bots to be admins in a channel/supergroup before they
can read messages there via ``get_messages``. Without admin status, the
HyperTG download path silently degrades to using fewer parallel clients
because helper bots cannot fetch file references from the dump chat.

This module finds every helper bot, checks its current status in the
configured ``LEECH_DUMP_CHAT``, and promotes any that aren't already
admins. It uses the user session first (recommended — full rights) and
falls back to the main bot session (must itself be admin with
``can_promote_members``).
"""

from asyncio import gather

from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import (
    ChatAdminRequired,
    PeerIdInvalid,
    RightForbidden,
    UserNotParticipant,
)
from pyrogram.types import ChatPrivileges

from ... import LOGGER
from ...core.config_manager import Config
from ...core.tg_client import TgClient


_ADMIN_STATUSES = (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)

_HELPER_PRIVILEGES = ChatPrivileges(
    can_manage_chat=True,
    can_delete_messages=True,
    can_manage_video_chats=False,
    can_restrict_members=False,
    can_promote_members=False,
    can_change_info=False,
    can_invite_users=True,
    can_post_messages=True,
    can_edit_messages=False,
    can_pin_messages=False,
    is_anonymous=False,
)


def _normalize_chat_id(raw):
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return raw  # username/link — Pyrogram will resolve


async def _promoter_clients():
    """Yield candidate clients that may have promote rights, in priority order."""
    seen = set()
    if TgClient.user is not None and id(TgClient.user) not in seen:
        seen.add(id(TgClient.user))
        yield "user", TgClient.user
    if TgClient.bot is not None and id(TgClient.bot) not in seen:
        seen.add(id(TgClient.bot))
        yield "bot", TgClient.bot


async def _ensure_one(chat_id, helper_idx, helper_bot):
    try:
        me = helper_bot.me
        if me is None:
            return helper_idx, "no-me", None
        uname = me.username or me.first_name or str(me.id)
    except Exception as e:  # noqa: BLE001
        return helper_idx, "no-me", str(e)

    # 1) Already admin?
    try:
        member = await helper_bot.get_chat_member(chat_id, me.id)
        if member.status in _ADMIN_STATUSES:
            return helper_idx, "already-admin", uname
    except UserNotParticipant:
        pass
    except (PeerIdInvalid, ChatAdminRequired):
        # Helper bot is not in the chat / has no view — must be added first
        return helper_idx, "not-in-chat", uname
    except Exception as e:  # noqa: BLE001
        # Unknown error — log and continue trying to promote anyway
        LOGGER.warning(
            f"helper_admin: get_chat_member failed for @{uname} in {chat_id}: {e}"
        )

    # 2) Try to promote using user session, then main bot
    last_err = None
    async for kind, promoter in _aiter_promoters():
        try:
            await promoter.promote_chat_member(
                chat_id=chat_id,
                user_id=me.id,
                privileges=_HELPER_PRIVILEGES,
            )
            return helper_idx, f"promoted-via-{kind}", uname
        except (ChatAdminRequired, RightForbidden) as e:
            last_err = f"{kind} has no promote rights: {e}"
        except PeerIdInvalid as e:
            last_err = f"{kind} cannot resolve {chat_id}: {e}"
        except Exception as e:  # noqa: BLE001
            last_err = f"{kind}: {type(e).__name__}: {e}"

    return helper_idx, "promote-failed", f"{uname} ({last_err})"


async def _aiter_promoters():
    """Async-iterator wrapper around _promoter_clients() for cleaner consumption."""
    async for item in _promoter_clients():
        yield item


async def ensure_helper_bots_admin():
    """Promote every helper bot AND helper user-session to admin in LEECH_DUMP_CHAT.

    Without this:
    - helper bots can't fetch file refs (HyperTG download falls back)
    - helper user sessions silently downgrade transmission to bot mode
      (because `can_manage_chat`/`can_delete_messages` checks fail) →
      uploads stay single-stream at 1 MB/s no matter how many you add.
    """
    raw_chat = getattr(Config, "LEECH_DUMP_CHAT", None)
    chat_id = _normalize_chat_id(raw_chat)
    bots = TgClient.helper_bots or {}
    users = TgClient.helper_users or {}
    if not chat_id or (not bots and not users):
        return

    LOGGER.info(
        f"helper_admin: ensuring {len(bots)} helper bot(s) + {len(users)} "
        f"helper user(s) are admin in {chat_id}"
    )

    tasks = []
    labels = []
    for idx, hbot in bots.items():
        tasks.append(_ensure_one(chat_id, f"bot-{idx}", hbot))
        labels.append(("helper-bot", idx))
    for idx, huser in users.items():
        tasks.append(_ensure_one(chat_id, f"user-{idx}", huser))
        labels.append(("helper-user", idx))

    results = await gather(*tasks, return_exceptions=True)

    promoted = already = failed = 0
    for (kind, idx), r in zip(labels, results):
        if isinstance(r, BaseException):
            failed += 1
            LOGGER.warning(f"helper_admin: {kind}-{idx} unexpected error: {r}")
            continue
        _idx, status, info = r
        tag = f"{kind} @{info}" if info else f"{kind}-{idx}"
        if status == "already-admin":
            already += 1
            LOGGER.info(f"helper_admin: {tag} already admin in {chat_id}")
        elif status.startswith("promoted-via-"):
            promoted += 1
            via = status.split("-", 2)[-1]
            LOGGER.info(f"helper_admin: promoted {tag} via {via}")
        elif status == "not-in-chat":
            failed += 1
            LOGGER.warning(
                f"helper_admin: {tag} is NOT in chat {chat_id} — invite "
                "this account to the chat once, then it auto-promotes on next restart"
            )
        else:
            failed += 1
            LOGGER.warning(f"helper_admin: could not promote {tag}")

    LOGGER.info(
        f"helper_admin: done — already_admin={already} promoted={promoted} "
        f"failed={failed}"
    )
