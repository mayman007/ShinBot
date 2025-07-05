import logging
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMember
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, UserAdminInvalid
from pyrogram.handlers import MessageHandler
from utils.decorators import admin_only
from utils.helpers import extract_user_and_reason
from pyrogram import types

logger = logging.getLogger(__name__)

async def check_bot_promote_permissions(client: Client, chat_id: int) -> tuple[bool, str]:
    """Check if bot has permission to promote/demote members"""
    try:
        me = await client.get_me()
        bot_member = await client.get_chat_member(chat_id, me.id)
        
        logger.info(f"Bot status: {bot_member.status}")
        
        # Check if bot is admin and has promote privileges
        if hasattr(bot_member, 'privileges') and bot_member.privileges:
            can_promote = bot_member.privileges.can_promote_members
            logger.info(f"Bot can_promote_members: {can_promote}")
            if not can_promote:
                return False, "I don't have the 'Add new admins' permission. Please grant this permission in chat settings."
            return True, ""
        
        # Check if bot has admin status
        status_str = str(bot_member.status).lower()
        if 'administrator' in status_str or 'admin' in status_str:
            return True, ""
        
        return False, "I'm not an administrator in this chat."
    except Exception as e:
        logger.error(f"Error checking bot permissions: {e}")
        return False, f"Error checking permissions: {str(e)}"

@admin_only
async def promote_user(client: Client, message: Message):
    """Promote a user to administrator"""
    try:
        # Check bot permissions first
        can_promote, error_msg = await check_bot_promote_permissions(client, message.chat.id)
        if not can_promote:
            await message.reply(f"❌ {error_msg}")
            return
        
        user, reason = await extract_user_and_reason(client, message)
        if not user:
            await message.reply("❌ Please specify a user to promote.\n**Usage:** `/promote @username [title]` or reply to a message with `/promote [title]`")
            return
        
        # Check if trying to promote yourself
        if user.id == message.from_user.id:
            await message.reply("❌ You cannot promote yourself!")
            return
        
        # Check if trying to promote the bot
        me = await client.get_me()
        if user.id == me.id:
            await message.reply("❌ I cannot promote myself!")
            return
        
        # Check if user is already an admin
        try:
            member = await client.get_chat_member(message.chat.id, user.id)
            status_str = str(member.status).lower()
            if ('owner' in status_str or 'creator' in status_str or 
                'administrator' in status_str or 'admin' in status_str):
                await message.reply(f"❌ {user.first_name} is already an administrator.")
                return
        except UserNotParticipant:
            await message.reply(f"❌ {user.first_name} is not in this chat.")
            return
        
        # Use reason as custom title if provided, otherwise use default
        custom_title = reason if reason and len(reason) <= 16 else None
        
        # Try promoting with minimal permissions first
        try:
            await client.promote_chat_member(
                message.chat.id, 
                user.id,
                privileges=types.ChatPrivileges(
                    can_manage_chat=False,
                    can_delete_messages=True,
                    can_manage_video_chats=False,
                    can_restrict_members=True,
                    can_promote_members=False,
                    can_change_info=False,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_manage_topics=False
                )
            )
        except Exception as e:
            logger.error(f"First promotion attempt failed: {e}")
            # Try with even more minimal permissions
            await client.promote_chat_member(
                message.chat.id, 
                user.id,
                privileges=types.ChatPrivileges(
                    can_manage_chat=False,
                    can_delete_messages=True,
                    can_manage_video_chats=False,
                    can_restrict_members=False,
                    can_promote_members=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                    can_manage_topics=False
                )
            )
        
        # Set custom title if provided (after promotion)
        if custom_title:
            try:
                await client.set_administrator_title(message.chat.id, user.id, custom_title)
            except Exception as e:
                logger.warning(f"Failed to set custom title: {e}")
        
        promote_text = f"⬆️ **User Promoted**\n"
        promote_text += f"**User:** {user.mention}\n"
        promote_text += f"**Admin:** {message.from_user.mention}\n"
        if custom_title:
            promote_text += f"**Title:** {custom_title}"
        
        await message.reply(promote_text)
        logger.info(f"User {user.id} promoted in chat {message.chat.id} by {message.from_user.id}")
        
    except ChatAdminRequired:
        await message.reply("❌ I need admin privileges with 'Add new admins' permission to promote users.")
    except Exception as e:
        await message.reply(f"❌ Error promoting user: {str(e)}")
        logger.error(f"Error in promote command: {e}")

@admin_only
async def demote_user(client: Client, message: Message):
    """Demote a user from administrator"""
    try:
        # Check bot permissions first
        can_promote, error_msg = await check_bot_promote_permissions(client, message.chat.id)
        if not can_promote:
            await message.reply(f"❌ {error_msg}")
            return
        
        user, reason = await extract_user_and_reason(client, message)
        if not user:
            await message.reply("❌ Please specify a user to demote.\n**Usage:** `/demote @username [reason]` or reply to a message with `/demote [reason]`")
            return
        
        # Check if trying to demote yourself
        if user.id == message.from_user.id:
            await message.reply("❌ You cannot demote yourself!")
            return
        
        # Check if trying to demote the bot
        me = await client.get_me()
        if user.id == me.id:
            await message.reply("❌ I cannot demote myself!")
            return
        
        # Check if user is actually an admin
        try:
            member = await client.get_chat_member(message.chat.id, user.id)
            
            # Use the actual ChatMemberStatus enum values
            if member.status == "creator":
                await message.reply(f"❌ Cannot demote {user.first_name} - user is the chat owner.")
                return
            elif member.status not in ["administrator"]:
                await message.reply(f"❌ {user.first_name} is not an administrator.")
                return
                
        except UserNotParticipant:
            await message.reply(f"❌ {user.first_name} is not in this chat.")
            return
        
        # Try to demote the user
        try:
            await client.promote_chat_member(
                message.chat.id, 
                user.id,
                privileges=types.ChatPrivileges(
                    can_manage_chat=False,
                    can_delete_messages=False,
                    can_manage_video_chats=False,
                    can_restrict_members=False,
                    can_promote_members=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                    can_manage_topics=False
                )
            )
            
            demote_text = f"⬇️ **User Demoted**\n"
            demote_text += f"**User:** {user.mention}\n"
            demote_text += f"**Admin:** {message.from_user.mention}\n"
            if reason:
                demote_text += f"**Reason:** {reason}"
            
            await message.reply(demote_text)
            logger.info(f"User {user.id} demoted in chat {message.chat.id} by {message.from_user.id}")
            
        except Exception as demote_error:
            error_msg = str(demote_error).lower()
            logger.error(f"Demote error details: {demote_error}")
            
            if "bot_channels_na" in error_msg:
                # This specific error means Telegram doesn't allow this bot action
                await message.reply(
                    f"❌ Cannot demote {user.first_name}.\n\n"
                    "**Reason:** Telegram restricts bots from demoting this admin due to security policies.\n\n"
                    "**Solution:** The group owner or another admin with sufficient privileges needs to demote this user manually through the group settings."
                )
            elif "user_creator" in error_msg:
                await message.reply(f"❌ Cannot demote {user.first_name} - user is the chat owner.")
            elif "user_admin_invalid" in error_msg:
                await message.reply(f"❌ Cannot demote {user.first_name} - user has protected admin status.")
            else:
                await message.reply(f"❌ Error demoting user: {str(demote_error)}")
        
    except ChatAdminRequired:
        await message.reply("❌ I need admin privileges with 'Add new admins' permission to demote users.")
    except Exception as e:
        await message.reply(f"❌ Error demoting user: {str(e)}")
        logger.error(f"Error in demote command: {e}")
    except Exception as e:
        await message.reply(f"❌ Error demoting user: {str(e)}")
        logger.error(f"Error in demote command: {e}")
