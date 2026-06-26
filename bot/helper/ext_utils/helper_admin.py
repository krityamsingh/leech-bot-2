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
    """Promote every helper bot to admin in LEECH_DUMP_CHAT (best-effort)."""
    raw_chat = getattr(Config, "LEECH_DUMP_CHAT", None)
    chat_id = _normalize_chat_id(raw_chat)
    helpers = TgClient.helper_bots
    if not chat_id or not helpers:
        return

    LOGGER.info(
        f"helper_admin: ensuring {len(helpers)} helper bot(s) are admin in {chat_id}"
    )
    results = await gather(
        *(_ensure_one(chat_id, idx, hbot) for idx, hbot in helpers.items()),
        return_exceptions=True,
    )

    promoted = already = failed = 0
    for r in results:
        if isinstance(r, BaseException):
            failed += 1
            LOGGER.warning(f"helper_admin: unexpected error: {r}")
            continue
        _idx, status, info = r
        if status == "already-admin":
            already += 1
            LOGGER.info(f"helper_admin: @{info} already admin in {chat_id}")
        elif status.startswith("promoted-via-"):
            promoted += 1
            via = status.split("-", 2)[-1]
            LOGGER.info(
                f"helper_admin: promoted @{info} to admin in {chat_id} via {via}"
            )
        elif status == "not-in-chat":
            failed += 1
            LOGGER.warning(
                f"helper_admin: @{info} is NOT a member of {chat_id} — "
                "add the bot to the chat first, then it will be auto-promoted"
            )
        else:
            failed += 1
            LOGGER.warning(f"helper_admin: could not promote {info}")

    LOGGER.info(
        f"helper_admin: done — already_admin={already} promoted={promoted} "
        f"failed={failed}"
    )
