from functools import wraps
from pyrogram.types import Message
from pyrogram.errors import UserAdminInvalid
from pyrogram.enums import ChatMemberStatus
import logging
from .helpers import extract_user_and_reason

logger = logging.getLogger(__name__)

async def check_admin_permissions(client, chat_id: int, user_id: int):
    """Check if user has admin permissions with comprehensive debugging."""
    try:
        # First, check if this is a private chat
        chat = await client.get_chat(chat_id)
        if chat.type.name.lower() == "private":
            logger.info(f"Private chat detected, allowing command for user {user_id}")
            return True
        
        logger.info(f"Checking admin permissions for user {user_id} in chat {chat_id} ({chat.type})")
        
        # Check bot's own permissions first
        try:
            bot_member = await client.get_chat_member(chat_id, "me")
            logger.info(f"Bot status in chat: {bot_member.status}")
            if bot_member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                logger.warning("Bot is not an admin in this chat")
                return False
        except Exception as e:
            logger.warning(f"Could not check bot admin status: {e}")
        
        # Try to get user's member status
        try:
            member = await client.get_chat_member(chat_id, user_id)
            logger.info(f"User {user_id} status: {member.status}")

            if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
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
            if chat.type.name.lower() != "private":
                try:
                    bot_member = await client.get_chat_member(message.chat.id, "me")
                    if bot_member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
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

def protect_admins(func):
    """
    Decorator to prevent a command from affecting another admin.
    It extracts the target user from the message and checks if they are an admin.
    This should be applied after @admin_only.
    """
    @wraps(func)
    async def wrapper(client, message: Message):
        # This decorator should only apply in group chats where admin concepts exist
        chat = await client.get_chat(message.chat.id)
        if chat.type.name.lower() == "private":
            return await func(client, message)

        # Extract the user being targeted by the command
        target_user, _ = await extract_user_and_reason(client, message)

        if not target_user:
            # Let the command handler deal with no user found.
            # The handler should reply with "user not found" or similar.
            return await func(client, message)

        # Prevent users from targeting themselves
        if target_user.id == message.from_user.id:
            await message.reply("❌ You cannot perform this action on yourself.")
            return

        # Check if the target user is an admin
        is_target_admin = await check_admin_permissions(client, message.chat.id, target_user.id)
        if is_target_admin:
            await message.reply("❌ You cannot use this command on an administrator.")
            return

        # If target is not an admin, proceed with the original function
        return await func(client, message)

    return wrapper