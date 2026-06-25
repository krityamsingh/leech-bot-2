from ..helper.ext_utils.bot_utils import COMMAND_USAGE, new_task
from ..helper.ext_utils.help_messages import (
    YT_HELP_DICT,
    MIRROR_HELP_DICT,
    CLONE_HELP_DICT,
)
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    edit_message,
    delete_message,
    send_message,
)
from ..helper.ext_utils.help_messages import help_string


HELP_PAGE_SIZE = 12


def _help_entries():
    entries = []
    for line in help_string.splitlines():
        line = line.strip()
        if not line.startswith("/"):
            continue
        commands, _, description = line.partition(": ")
        if not description:
            continue
        primary = commands.split(" or ", 1)[0]
        entries.append((primary, commands, description))
    return entries


def _help_menu(page=0):
    entries = _help_entries()
    pages = [
        entries[i : i + HELP_PAGE_SIZE]
        for i in range(0, len(entries), HELP_PAGE_SIZE)
    ]
    page = max(0, min(page, len(pages) - 1)) if pages else 0
    buttons = ButtonMaker()

    for index, (primary, _, _) in enumerate(pages[page] if pages else []):
        entry_index = (page * HELP_PAGE_SIZE) + index
        buttons.data_button(primary, f"help cmd {entry_index} {page}")

    if len(pages) > 1:
        if page > 0:
            buttons.data_button("⫷", f"help menu {page - 1}", position="footer")
        if page < len(pages) - 1:
            buttons.data_button("⫸", f"help menu {page + 1}", position="footer")
    buttons.data_button("Close", "help close", position="footer")

    msg = (
        "<b>Bot Commands</b>\n"
        "Tap a command to view its usage. Try each command without arguments for more details."
    )
    if pages:
        msg += f"\n\nPage {page + 1}/{len(pages)}"
    return msg, buttons.build_menu(2, f_cols=3)


def _command_help(index, page):
    entries = _help_entries()
    if index < 0 or index >= len(entries):
        return _help_menu(page)

    primary, commands, description = entries[index]
    buttons = ButtonMaker()
    buttons.data_button("Back", f"help menu {page}")
    buttons.data_button("Close", "help close")
    msg = (
        f"<b>{primary}</b>\n\n"
        f"<b>Commands:</b> <code>{commands}</code>\n"
        f"<b>Usage:</b> {description}\n\n"
        "Send it without arguments for more details."
    )
    return msg, buttons.build_menu(2)


@new_task
async def arg_usage(_, query):
    data = query.data.split()
    message = query.message
    await query.answer()
    if data[1] == "close":
        return await delete_message(message, message.reply_to_message)
    if data[1] == "menu":
        page = int(data[2]) if len(data) > 2 else 0
        msg, buttons = _help_menu(page)
        return await edit_message(message, msg, buttons)
    if data[1] == "cmd":
        index = int(data[2])
        page = int(data[3]) if len(data) > 3 else 0
        msg, buttons = _command_help(index, page)
        return await edit_message(message, msg, buttons)
    pg_no = int(data[3])
    if data[1] == "nex":
        if data[2] == "mirror":
            await edit_message(
                message, COMMAND_USAGE["mirror"][0], COMMAND_USAGE["mirror"][pg_no + 1]
            )
        elif data[2] == "yt":
            await edit_message(
                message, COMMAND_USAGE["yt"][0], COMMAND_USAGE["yt"][pg_no + 1]
            )
        elif data[2] == "clone":
            await edit_message(
                message, COMMAND_USAGE["clone"][0], COMMAND_USAGE["clone"][pg_no + 1]
            )
    elif data[1] == "pre":
        if data[2] == "mirror":
            await edit_message(
                message, COMMAND_USAGE["mirror"][0], COMMAND_USAGE["mirror"][pg_no - 1]
            )
        elif data[2] == "yt":
            await edit_message(
                message, COMMAND_USAGE["yt"][0], COMMAND_USAGE["yt"][pg_no - 1]
            )
        elif data[2] == "clone":
            await edit_message(
                message, COMMAND_USAGE["clone"][0], COMMAND_USAGE["clone"][pg_no - 1]
            )
    elif data[1] == "back":
        if data[2] == "m":
            await edit_message(
                message, COMMAND_USAGE["mirror"][0], COMMAND_USAGE["mirror"][pg_no + 1]
            )
        elif data[2] == "y":
            await edit_message(
                message, COMMAND_USAGE["yt"][0], COMMAND_USAGE["yt"][pg_no + 1]
            )
        elif data[2] == "c":
            await edit_message(
                message, COMMAND_USAGE["clone"][0], COMMAND_USAGE["clone"][pg_no + 1]
            )
    elif data[1] == "mirror":
        buttons = ButtonMaker()
        buttons.data_button("Back", f"help back m {pg_no}")
        button = buttons.build_menu()
        await edit_message(message, MIRROR_HELP_DICT[data[2]], button)
    elif data[1] == "yt":
        buttons = ButtonMaker()
        buttons.data_button("Back", f"help back y {pg_no}")
        button = buttons.build_menu()
        await edit_message(message, YT_HELP_DICT[data[2]], button)
    elif data[1] == "clone":
        buttons = ButtonMaker()
        buttons.data_button("Back", f"help back c {pg_no}")
        button = buttons.build_menu()
        await edit_message(message, CLONE_HELP_DICT[data[2]], button)


@new_task
async def bot_help(_, message):
    msg, buttons = _help_menu()
    await send_message(message, msg, buttons)
