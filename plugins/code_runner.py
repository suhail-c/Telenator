import asyncio
import html
import logging
import random
import re
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from time import perf_counter
from traceback import format_exc
from typing import Optional

import pyrogram
from pyrogram import Client, enums, filters, raw, types
from pyrogram import utils as pyroutils
from pyrogram.types import LinkPreviewOptions, Message

from utils.db import db
from utils.filters import command
from utils.misc import modules_help
from utils.scripts import paste_yaso, shell_exec

log = logging.getLogger(__name__)


async def aexec(code, client: Client, message: Message, timeout=None):
    exec_globals = {
        "app": client,
        "c": client,
        "m": message,
        "r": message.reply_to_message,
        "u": message.from_user,
        "ru": getattr(message.reply_to_message, "from_user", None),
        "p": print,
        "here": message.chat.id,
        "db": db,
        "raw": raw,
        "rf": raw.functions,
        "rt": raw.types,
        "types": types,
        "enums": enums,
        "utils": pyroutils,
        "pyrogram": pyrogram,
        "asyncio": asyncio
    }

    exec(
        "async def __todo(client, message, *args):\n"
        + "".join(f"\n {_l}" for _l in code.split("\n")),
        exec_globals,
    )

    f = StringIO()

    with redirect_stdout(f):
        await asyncio.wait_for(exec_globals["__todo"](client, message), timeout=timeout)

    return f.getvalue()


code_result = (
    "<blockquote><emoji id=5431376038628171216>💻</emoji> Code:</blockquote>\n"
    '<pre language="{pre_language}">{code}</pre>\n\n'
    "{result}"
)


def extract_code_from_reply(message: Message, language: str = None) -> Optional[str]:
    """Извлекает python-код из реплая или возвращает None."""
    if not message.reply_to_message:
        return None

    if language and message.reply_to_message.entities:
        for entity in message.reply_to_message.entities:
            if entity.type == enums.MessageEntityType.PRE and entity.language == language:
                return message.reply_to_message.content[
                    entity.offset : entity.offset + entity.length
                ]

    return message.reply_to_message.content


@Client.on_message(~filters.scheduled & command(["py", "rpy"]) & filters.me & ~filters.forwarded)
async def python_exec(client: Client, message: Message):
    code = ""

    if message.command[0] == "rpy":
        code = extract_code_from_reply(message, "python") or ""
    elif message.command[0] == "py":
        parts = message.content.split(maxsplit=1)
        code = parts[1] if len(parts) > 1 else ""

    if not code:
        return await message.edit_text("<b>Code to execute isn't provided</b>")

    code = code.replace("\u00a0", "")

    await message.edit_text("<b><emoji id=5821116867309210830>🔃</emoji> Executing...</b>")

    try:
        start_time = perf_counter()
        result = await aexec(code, client, message, timeout=db.get("shell", "timeout", 60))
        elapsed = round(perf_counter() - start_time, 5)
    except asyncio.TimeoutError:
        return await message.edit_text(
            code_result.format(
                pre_language="python",
                code=html.escape(code),
                result="<blockquote><emoji id=5465665476971471368>❌</emoji> Timeout Error!</blockquote>",
            ),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception as e:
        with redirect_stderr(StringIO()):
            err = "\n".join(
                line
                for i, line in enumerate(format_exc().splitlines(), start=1)
                if not 2 <= i <= 9
            )

        log.info("Exception from executed code:")
        for line in err.splitlines():
            log.info(f"\033[31m{line}\033[0m")

        return await message.edit_text(
            code_result.format(
                pre_language="python",
                code=html.escape(code),
                result=f"<blockquote><emoji id=5465665476971471368>❌</emoji> {e.__class__.__name__}: {e}</blockquote>\nTraceback: {html.escape(await paste_yaso(err))}",
            ),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

    # Replace account phone number to anonymous
    random_phone_number = "".join(str(random.randint(0, 9)) for _ in range(8))
    result = result.replace(client.me.phone_number, f"888{random_phone_number}")

    paste_result = ""

    if not result:
        result = "No result"
    elif len(result) > 512:
        paste_result = html.escape(await paste_yaso(result))

        if paste_result == "Pasting failed":
            error_bytes = BytesIO(result.encode("utf-8"))
            error_bytes.seek(0)
            error_bytes.name = "result.log"

            return await message.reply_document(
                document=error_bytes,
                caption=code_result.format(
                    pre_language="python",
                    code=html.escape(code),
                    result=f"<blockquote><emoji id=5472164874886846699>✨</emoji> Result is too long</blockquote>\n"
                    f"<i>Completed in {elapsed}s.</i>",
                ),
            )

    elif not re.match(r"^(https?):\/\/[^\s\/$.?#].[^\s]*$", result):
        result = f"<pre>{html.escape(result)}</pre>"

    if paste_result:
        return await message.edit_text(
            code_result.format(
                pre_language="python",
                code=html.escape(code),
                result=f"<blockquote><emoji id=5472164874886846699>✨</emoji> Result:</blockquote>\n"
                f"<pre>{result[:512]}...</pre>\n<blockquote><b><a href='{paste_result}'>More</a></b></blockquote>\n"
                f"<i>Completed in {elapsed}s.</i>",
            ),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    else:
        return await message.edit_text(
            code_result.format(
                pre_language="python",
                code=html.escape(code),
                result=f"<blockquote><emoji id=5472164874886846699>✨</emoji> Result:</blockquote>\n"
                f"{result}\n"
                f"<i>Completed in {elapsed}s.</i>",
            ),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )


module = modules_help.add_module("code_runner", __file__)
module.add_command("py", "Execute Python code", "[code]")
module.add_command("rpy", "Execute Python code from reply")
