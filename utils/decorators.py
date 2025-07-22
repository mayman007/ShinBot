from functools import wraps
from pyrogram.types import Message
from pyrogram.errors import UserAdminInvalid
import logging

logger = logging.getLogger(__name__)

async def check_admin_permissions(client, chat_id: int, user_id: int):
    """Check if user has admin permissions with comprehensive debugging."""
    try:
        # First, check if this is a private chat
        chat = await client.get_chat(chat_id)
        if chat.type == "private":
            logger.info(f"Private chat detected, allowing command for user {user_id}")
            return True
        
        logger.info(f"Checking admin permissions for user {user_id} in chat {chat_id} ({chat.type})")
        
        # Check bot's own permissions first
        try:
            bot_member = await client.get_chat_member(chat_id, "me")
            logger.info(f"Bot status in chat: {bot_member.status}")
            status_str = str(bot_member.status).lower()
            if not ('administrator' in status_str or 'creator' in status_str or 'owner' in status_str):
                logger.warning("Bot is not an admin in this chat")
                return False
        except Exception as e:
            logger.warning(f"Could not check bot admin status: {e}")
        
        # Try to get user's member status
        try:
            member = await client.get_chat_member(chat_id, user_id)
            logger.info(f"User {user_id} status: {member.status}")
            
            status_str = str(member.status).lower()
            if (member.status == 'creator' or 
                member.status == 'owner' or 
                'owner' in status_str or 
                'creator' in status_str or
                member.status == 'administrator' or 
                'administrator' in status_str or
                'admin' in status_str):
                logger.info(f"User {user_id} is admin/owner")
                return True
            else:
                logger.info(f"User {user_id} is not an admin (status: {member.status})")
                return False
                
        except UserAdminInvalid as e:
            logger.warning(f"UserAdminInvalid for user {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error getting member info for user {user_id}: {e}")
            
            # Fallback: try to get administrators list
            try:
                logger.info("Trying fallback method: checking administrators list")
                admins = await client.get_chat_administrators(chat_id)
                logger.info(f"Found {len(admins)} administrators")
                
                for admin in admins:
                    if admin.user.id == user_id:
                        logger.info(f"User {user_id} found in administrators list with status: {admin.status}")
                        return True
                
                logger.info(f"User {user_id} not found in administrators list")
                return False
                
            except Exception as e2:
                logger.error(f"Fallback admin check also failed: {e2}")
                return False
                
    except Exception as e:
        logger.error(f"Unexpected error in admin check: {e}")
        return False

def admin_only(func):
    """Decorator to restrict command to admins and owners only"""
    @wraps(func)
    async def wrapper(client, message: Message):
        try:
            # First check if bot is admin (except in private chats)
            chat = await client.get_chat(message.chat.id)
            if chat.type != "private":
                try:
                    bot_member = await client.get_chat_member(message.chat.id, "me")
                    bot_status_str = str(bot_member.status).lower()
                    if not ('administrator' in bot_status_str or 'creator' in bot_status_str or 'owner' in bot_status_str):
                        await message.reply("❌ I need administrator permissions to execute admin commands.")
                        return
                except Exception as e:
                    logger.error(f"Could not check bot admin status: {e}")
                    await message.reply("❌ Unable to verify bot permissions.")
                    return
            
            # Use the robust admin checking function
            is_admin = await check_admin_permissions(client, message.chat.id, message.from_user.id)
            if not is_admin:
                await message.reply("❌ This command is only available to administrators.")
                return
            
            return await func(client, message)
                
        except Exception as e:
            logger.error(f"Unexpected error in admin_only decorator: {e}")
            await message.reply("❌ An unexpected error occurred.")
            return
    
    return wrapper