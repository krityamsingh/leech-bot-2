#!/usr/bin/env python3
from pyrogram.filters import create

from bot import OWNER_ID


class CustomFilters:

    async def owner_filter(self, _, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return uid == OWNER_ID

    owner = create(owner_filter)

    async def authorized_user(self, _, message):
        return True

    authorized = create(authorized_user)

    async def authorized_usetting(self, _, message):
        return True

    authorized_uset = create(authorized_usetting)

    async def sudo_user(self, _, message):
        user = message.from_user or message.sender_chat
        uid = user.id
        return bool(
            uid == OWNER_ID or uid in user_data and user_data[uid].get("is_sudo")
        )

    sudo = create(sudo_user)

    async def blacklist_user(self, _, message):
        return False

    blacklisted = create(blacklist_user)
