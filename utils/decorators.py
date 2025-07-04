from functools import wraps
from pyrogram.types import Message

def admin_only(func):
    """Decorator to restrict command to admins and owners only"""
    @wraps(func)
    async def wrapper(client, message: Message):
        try:
            # Get user's status in the chat
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            
            # Check if user is admin or owner
            if member.status in ["administrator", "creator"]:
                return await func(client, message)
            else:
                await message.reply("❌ This command is only available to administrators.")
                return
                
        except Exception as e:
            await message.reply("❌ Error checking permissions.")
            return
    
    return wrapper
