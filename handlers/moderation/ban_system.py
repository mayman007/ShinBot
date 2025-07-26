import logging
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, UserAdminInvalid
from pyrogram.enums import ChatMembersFilter
from utils.decorators import admin_only, protect_admins
from utils.helpers import create_pagination_keyboard, extract_user_and_reason, split_text_into_pages
from utils.usage import save_usage

logger = logging.getLogger(__name__)

pagination_data = {}

@admin_only
@protect_admins
async def ban_user(client: Client, message: Message):
    """Ban a user from the chat"""
    chat = message.chat
    await save_usage(chat, "ban")
    
    try:
        user, reason = await extract_user_and_reason(client, message)
        if not user:
            await message.reply("❌ Please specify a user to ban.\n**Usage:** `/ban @username [reason]` or reply to a message with `/ban [reason]`")
            return
        
        # Check if trying to ban yourself
        if user.id == message.from_user.id:
            await message.reply("❌ You cannot ban yourself!")
            return
        
        # Check if trying to ban the bot
        me = await client.get_me()
        if user.id == me.id:
            await message.reply("❌ I cannot ban myself!")
            return
        
        # Check if user is already banned
        try:
            member = await client.get_chat_member(message.chat.id, user.id)
            if member.status in ["kicked", "banned"]:
                await message.reply(f"❌ {user.first_name} is already banned.")
                return
            
            # Check if trying to ban an admin
            status_str = str(member.status).lower()
            if ('owner' in status_str or 'creator' in status_str or 
                'administrator' in status_str or 'admin' in status_str):
                await message.reply(f"❌ Cannot ban {user.first_name} - user is an admin.")
                return
                
        except UserNotParticipant:
            await message.reply(f"❌ {user.first_name} is not in this chat.")
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
    chat = message.chat
    await save_usage(chat, "unban")
    
    try:
        user, reason = await extract_user_and_reason(client, message)
        if not user:
            await message.reply("❌ Please specify a user to unban.\n**Usage:** `/unban @username [reason]` or reply to a message with `/unban [reason]`")
            return
        
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

# ---------------------------
# List all banned users command (Final Correction)
# ---------------------------
@admin_only
async def banslist_command(client: Client, message: Message):
    """Lists all banned users in the chat."""
    chat = message.chat
    sender = message.from_user
    
    logger.info(f"Banslist command called by user {sender.id} in chat {chat.id}")
    await save_usage(chat, "banslist")
    
    try:
        banned_members = []
        async for member in client.get_chat_members(chat.id, filter=ChatMembersFilter.BANNED):
            banned_members.append(member)

        if not banned_members:
            await message.reply("✅ No users are currently banned in this chat.")
            return
            
        lines = [f"🔨 **Banned Users in {chat.title or 'this chat'}** ({len(banned_members)} total)\n"]
        
        for member in banned_members:
            # We can only get the user's information, not who banned them or why.
            user = member.user
            lines.append(f"👤 {user.mention} (`{user.id}`)")
        
        # Pagination logic remains the same
        pages = await split_text_into_pages(lines)
        
        if len(pages) == 1:
            # Add a newline at the end for better spacing in the final message
            final_text = "\n".join(lines)
            await message.reply(final_text, disable_web_page_preview=True)
        else:
            callback_prefix = f"banslist_{chat.id}"
            
            pagination_data[callback_prefix] = {
                'pages': pages,
                'chat_title': chat.title or 'this chat',
                'user_id': sender.id
            }
            
            keyboard = await create_pagination_keyboard(1, len(pages), callback_prefix)
            await message.reply(pages[0], reply_markup=keyboard, disable_web_page_preview=True)
            
    except ChatAdminRequired:
        await message.reply("❌ I need to be an admin with the 'can_restrict_members' permission to see the ban list.")
    except Exception as e:
        logger.error(f"Error in banslist_command for chat {chat.id}: {e}")
        await message.reply(f"❌ An error occurred while fetching the ban list: {str(e)}")