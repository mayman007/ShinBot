import logging
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMember
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, UserAdminInvalid
from pyrogram.handlers import MessageHandler
from utils.decorators import admin_only
from utils.helpers import extract_user_and_reason

logger = logging.getLogger(__name__)

@admin_only
async def ban_user(client: Client, message: Message):
    """Ban a user from the chat"""
    try:
        user, reason = await extract_user_and_reason(client, message)
        if not user:
            await message.reply("❌ Please specify a user to ban.")
            return
        
        # Check if user is already banned
        try:
            member = await client.get_chat_member(message.chat.id, user.id)
            if member.status in ["kicked", "banned"]:
                await message.reply(f"❌ {user.first_name} is already banned.")
                return
        except UserNotParticipant:
            await message.reply(f"❌ {user.first_name} is not in this chat.")
            return
        
        # Check if trying to ban an admin
        if member.status in ["administrator", "creator"]:
            await message.reply(f"❌ Cannot ban {user.first_name} - user is an admin.")
            return
        
        # Ban the user
        await client.ban_chat_member(message.chat.id, user.id)
        
        ban_text = f"🔨 **User Banned**\n"
        ban_text += f"**User:** {user.mention}\n"
        ban_text += f"**Admin:** {message.from_user.mention}\n"
        if reason:
            ban_text += f"**Reason:** {reason}"
        
        await message.reply(ban_text)
        logger.info(f"User {user.id} banned from chat {message.chat.id} by {message.from_user.id}")
        
    except ChatAdminRequired:
        await message.reply("❌ I need admin privileges to ban users.")
    except UserAdminInvalid:
        await message.reply("❌ Cannot ban this user.")
    except Exception as e:
        await message.reply(f"❌ Error banning user: {str(e)}")
        logger.error(f"Error in ban command: {e}")

@admin_only
async def unban_user(client: Client, message: Message):
    """Unban a user from the chat"""
    try:
        user, reason = await extract_user_and_reason(client, message)
        if not user:
            await message.reply("❌ Please specify a user to unban.")
            return
        
        # Check if user is actually banned
        try:
            member = await client.get_chat_member(message.chat.id, user.id)
            if member.status not in ["kicked", "banned"]:
                await message.reply(f"❌ {user.first_name} is not banned.")
                return
        except UserNotParticipant:
            # User is not in chat, try to unban anyway
            pass
        
        # Unban the user
        await client.unban_chat_member(message.chat.id, user.id)
        
        unban_text = f"✅ **User Unbanned**\n"
        unban_text += f"**User:** {user.mention}\n"
        unban_text += f"**Admin:** {message.from_user.mention}\n"
        if reason:
            unban_text += f"**Reason:** {reason}"
        
        await message.reply(unban_text)
        logger.info(f"User {user.id} unbanned from chat {message.chat.id} by {message.from_user.id}")
        
    except ChatAdminRequired:
        await message.reply("❌ I need admin privileges to unban users.")
    except Exception as e:
        await message.reply(f"❌ Error unbanning user: {str(e)}")
        logger.error(f"Error in unban command: {e}")
