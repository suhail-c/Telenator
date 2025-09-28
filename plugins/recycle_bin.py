from typing import List
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from cachetools import TTLCache
from utils.filters import command
from utils.misc import modules_help


deleted_messages = TTLCache(maxsize=5000, ttl=86400)

def store_deleted_message(chat_id, message_id):
    if chat_id not in deleted_messages:
        deleted_messages[chat_id] = []
    deleted_messages[chat_id].append(message_id)

def get_deleted_messages(chat_id):
    return deleted_messages.get(chat_id, [])
    
@Client.on_deleted_messages()
async def on_deleted_msg(client: Client, messages: List[Message]): 
    for message in messages:
        await send_message("me", message)
        store_deleted_message(message.chat.id, message.id)
        
@Client.on_message(command(["recover"]) & filters.me)        
async def recover_messages(client: Client, message: Message):  
   
    parts = message.content.split(maxsplit=1)
    chat_id = parts[1] if len(parts) > 1 else ""

    if not chat_id:
        return await message.edit_text("<b>Chat id isn't provided</b>")        
    
    deleted_msgs = get_deleted_messages(chat_id)
    
    for msg_id in deleted_msgs:  
        deleted_msg = client.message_cache[(chat_id, msg_id)]
        if not deleted_msg: continue
        if deleted_msg.service: continue
        
        chat_name = deleted_msg.sender_chat.full_name
        msg_from = deleted_msg.from_user.full_name if deleted_msg.from_user else chat_name
        caption = f"Chat: {chat_name}\nFrom: {msg_from}"
        media = deleted_msg.media
        text = deleted_msg.text
        
        if media:
            if deleted_msg.photo:
                content = deleted_msg.photo.file_id
                await client.send_photo("me", content, caption)
            elif deleted_msg.video:
                content = deleted_msg.video.file_id
                await client.send_video("me", content, caption)
            elif deleted_msg.audio:
                content = deleted_msg.audio.file_id
                await client.send_audio("me", content, caption)
            elif deleted_msg.document:
                content = deleted_msg.document.file_id
                await client.send_document("me", content, caption)
        else:
            content = text
            await client.send_message("me", f"{caption}\n\n<pre>{content}</pre>")

module = modules_help.add_module("recycle_bin", __file__)
module.add_command("recover", "Recover recent deleted messages from a chat", "[chat_id]")   
