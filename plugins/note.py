import base64
from io import BytesIO
from sqlite3 import OperationalError

from pyrogram import Client, enums, filters, types
from pyrogram.types import Message

from utils.db import db
from utils.filters import command
from utils.misc import modules_help
from utils.scripts import get_prefix


@Client.on_message(~filters.scheduled & command(["snote"]) & filters.me & ~filters.forwarded)
async def snote_handler(_, message: Message):
    args = message.text.split(maxsplit=2)

    if len(args) < 2:
        return await message.edit(
            f"<b>Example: <code>{get_prefix()}{message.command[0]} note_name</code></b>"
        )

    note_name = args[1]

    if len(args) == 3:
        note = args[2]
    
    elif message.reply_to_message:
        note = (message.reply_to_message.text or message.reply_to_message.caption or None)
        
    if not note: return
    db.set("core.notes", f"note_{note_name}", note)

    await message.edit(f"<b>Successfully saved note:</b> <code>{note_name}</code>")


@Client.on_message(~filters.scheduled & command(["note"]) & filters.me & ~filters.forwarded)
async def note_handler(_, message: Message):
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return await message.edit(
            f"<b>Example: <code>{get_prefix()}{message.command[0]} note_name</code></b>"
        )

    note_name = args[1]

    note = db.get("core.notes", f"note_{note_name}")

    if not note:
        return await message.edit(f"<b>No note with name:</b> <code>{note_name}</code>")

    await message.edit(note)


@Client.on_message(~filters.scheduled & command(["dnote"]) & filters.me & ~filters.forwarded)
async def dnote_handler(_, message: Message):
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        return await message.edit(
            f"<b>Example: <code>{get_prefix()}{message.command[0]} note_name</code></b>"
        )

    note_name = args[1]

    note = db.get("core.notes", f"note_{note_name}")

    if note:
        db.remove("core.notes", f"note_{note_name}")
        await message.edit(f"<b>Successfully deleted note:</b> <code>{note_name}</code>")
    else:
        await message.edit(f"<b>No note with name:</b> <code>{note_name}</code>")


@Client.on_message(~filters.scheduled & command(["notes"]) & filters.me & ~filters.forwarded)
async def notes_handler(_, message: Message):
    with db._lock:
        try:
            notes = db._cursor.execute("SELECT * FROM 'core.notes'").fetchall()
        except OperationalError as e:
            if "no such table" in str(e):
                return await message.edit("<b>No saved notes</b>")

    if not notes:
        return await message.edit("<b>No saved notes</b>")

    res = "Available notes:\n"

    for row in notes:
        res += f"<code>{row['var'].split('_', maxsplit=1)[1]}</code>\n"

    await message.edit(res)


module = modules_help.add_module("notes", __file__)
module.add_command("snote", "Save note", "[name]")
module.add_command("note", "Get saved note", "[name]")
module.add_command("dnote", "Delete saved note", "[name]")
module.add_command("notes", "Get saved notes list")
