import re
import asyncio
import aiosqlite
import logging
from datetime import datetime, timedelta
from pyrogram import Client, types
from pyrogram.errors import UserAdminInvalid
from utils.usage import save_usage
from utils.decorators import admin_only

logger = logging.getLogger(__name__)

async def init_mute_db():
    """Initialize the mute schedules database."""
    async with aiosqlite.connect("db/mute_schedules.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS mute_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    user_id INTEGER,
                    unmute_time TEXT,
                    reason TEXT,
                    muted_by INTEGER,
                    status TEXT DEFAULT 'active'
                )
            """)
            await connection.commit()
            logger.info("Mute schedules database initialized")

async def schedule_unmute(chat_id: int, user_id: int, unmute_time: datetime, reason: str, muted_by: int):
    """Schedule an automatic unmute."""
    await init_mute_db()
    async with aiosqlite.connect("db/mute_schedules.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO mute_schedules (chat_id, user_id, unmute_time, reason, muted_by) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user_id, unmute_time.isoformat(), reason, muted_by)
            )
            await connection.commit()
            logger.info(f"Scheduled unmute for user {user_id} in chat {chat_id} at {unmute_time}")

async def cancel_scheduled_unmute(chat_id: int, user_id: int):
    """Cancel a scheduled unmute for a user."""
    await init_mute_db()
    async with aiosqlite.connect("db/mute_schedules.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "UPDATE mute_schedules SET status = 'cancelled' WHERE chat_id = ? AND user_id = ? AND status = 'active'",
                (chat_id, user_id)
            )
            await connection.commit()
            logger.info(f"Cancelled scheduled unmute for user {user_id} in chat {chat_id}")

async def check_pending_unmutes(client: Client):
    """Check for and execute pending unmutes."""
    await init_mute_db()
    try:
        async with aiosqlite.connect("db/mute_schedules.db") as connection:
            async with connection.cursor() as cursor:
                now = datetime.now().isoformat()
                await cursor.execute(
                    "SELECT id, chat_id, user_id, reason FROM mute_schedules WHERE unmute_time <= ? AND status = 'active'",
                    (now,)
                )
                pending_unmutes = await cursor.fetchall()
                
                for unmute_id, chat_id, user_id, reason in pending_unmutes:
                    try:
                        # Unmute the user
                        await client.unban_chat_member(chat_id, user_id)
                        
                        # Mark as completed
                        await cursor.execute(
                            "UPDATE mute_schedules SET status = 'completed' WHERE id = ?",
                            (unmute_id,)
                        )
                        
                        # Try to send notification
                        try:
                            await client.send_message(
                                chat_id,
                                f"🔊 **Automatic Unmute**\n"
                                f"User has been automatically unmuted.\n"
                                f"**Reason:** {reason}"
                            )
                        except:
                            pass  # Don't fail if we can't send message
                        
                        logger.info(f"Auto-unmuted user {user_id} in chat {chat_id}")
                        
                    except Exception as e:
                        logger.error(f"Error auto-unmuting user {user_id} in chat {chat_id}: {e}")
                        # Mark as failed
                        await cursor.execute(
                            "UPDATE mute_schedules SET status = 'failed' WHERE id = ?",
                            (unmute_id,)
                        )
                
                await connection.commit()
                
    except Exception as e:
        logger.error(f"Error checking pending unmutes: {e}")

# Background task to check for pending unmutes
async def unmute_checker_task(client: Client):
    """Background task that runs every minute to check for pending unmutes."""
    while True:
        try:
            await check_pending_unmutes(client)
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Error in unmute checker task: {e}")
            await asyncio.sleep(60)

async def is_user_muted(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if a user is currently muted."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        # Check if user has restricted permissions (muted)
        if member.restricted_by and member.permissions:
            # If all main permissions are False, user is muted
            perms = member.permissions
            return not (perms.can_send_messages or 
                       perms.can_send_media_messages or 
                       perms.can_send_other_messages or 
                       perms.can_add_web_page_previews)
        return False
    except:
        return False

# ---------------------------
# Mute command
# ---------------------------
@admin_only
async def mute_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "mute")
    
    # Parse command arguments
    args = message.text.split()[1:]  # Remove command itself
    
    if not args:
        await message.reply("Please specify a user to mute.\n**Usage:** `/mute @username [time] [reason]`")
        return
    
    # Extract user (first argument)
    user_arg = args[0]
    target_user = None
    
    # Try to get user from mention or username
    if user_arg.startswith('@'):
        username = user_arg[1:]  # Remove @
        try:
            target_user = await client.get_users(username)
        except:
            await message.reply(f"❌ User {user_arg} not found.")
            return
    elif message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        await message.reply("Please mention a user with @ or reply to their message.\n**Usage:** `/mute @username [time] [reason]`")
        return
    
    # Validate target_user
    if not target_user or not hasattr(target_user, 'id') or target_user.id is None:
        await message.reply("❌ Invalid user.")
        return
    
    # Check if user is already muted
    if await is_user_muted(client, chat.id, target_user.id):
        await message.reply(f"❌ User {target_user.mention} is already muted.")
        return
    
    # Parse remaining arguments for time and reason
    duration = None
    reason_parts = []
    
    for arg in args[1:]:  # Skip user argument
        time_match = re.match(r'^(\d+)([hmds])$', arg.lower())
        if time_match and duration is None:  # Only take first time found
            amount = int(time_match.group(1))
            unit = time_match.group(2)
            if unit == 'h':
                duration = amount * 60  # hours to minutes
            elif unit == 'd':
                duration = amount * 24 * 60  # days to minutes
            elif unit == 'm':
                duration = amount  # already in minutes
            elif unit == 's':
                duration = amount / 60  # seconds to minutes
        else:
            reason_parts.append(arg)
    
    reason = ' '.join(reason_parts) if reason_parts else "No reason provided"
    
    # Calculate until when the user will be muted (None for infinite)
    mute_until = None if duration is None else datetime.now() + timedelta(minutes=duration)
    
    try:
        # Apply mute restriction
        if mute_until:
            # Temporary mute with expiration
            await client.restrict_chat_member(
                chat.id,
                target_user.id,
                types.ChatPermissions(), # No permissions
                until_date=mute_until
            )
        else:
            # Permanent mute (no until_date parameter)
            await client.restrict_chat_member(
                chat.id,
                target_user.id,
                types.ChatPermissions() # No permissions
            )
        
        # Schedule automatic unmute if duration is specified
        if mute_until:
            await schedule_unmute(chat.id, target_user.id, mute_until, reason, message.from_user.id)
        
        # Send confirmation message
        if duration is None:
            mute_time_str = "indefinitely"
        else:
            if duration >= 60:
                hours = duration // 60
                minutes = duration % 60
                if hours > 0 and minutes > 0:
                    mute_time_str = f"for {hours}h {minutes}m"
                elif hours > 0:
                    mute_time_str = f"for {hours}h"
                else:
                    mute_time_str = f"for {minutes}m"
            elif duration < 1:
                seconds = int(duration * 60)
                mute_time_str = f"for {seconds}s"
            else:
                mute_time_str = f"for {int(duration)}m"
        
        await message.reply_text(
            f"🔇 **User Muted**\n"
            f"**User:** {target_user.mention}\n"
            f"**Duration:** {mute_time_str}\n"
            f"**Reason:** {reason}\n"
            f"**Admin:** {message.from_user.mention}"
            + (f"\n**Auto-unmute:** {mute_until.strftime('%Y-%m-%d %H:%M:%S')}" if mute_until else "")
        )
    except UserAdminInvalid:
        await message.reply("❌ I need admin privileges to mute users.")
    except Exception as e:
        logger.error(f"Error in mute command: {e}")
        await message.reply(f"❌ An error occurred: {str(e)}")

# ---------------------------
# Unmute command
# ---------------------------
@admin_only
async def unmute_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "unmute")
    
    # Parse command arguments
    args = message.text.split()[1:]  # Remove command itself
    
    target_user = None
    reason_parts = []
    
    if args:
        # Extract user (first argument)
        user_arg = args[0]
        
        # Try to get user from mention or username
        if user_arg.startswith('@'):
            username = user_arg[1:]  # Remove @
            try:
                target_user = await client.get_users(username)
            except:
                await message.reply(f"❌ User {user_arg} not found.")
                return
            reason_parts = args[1:]  # Remaining args are reason
        else:
            reason_parts = args  # All args are reason if no @ mention
    
    # If no user from args, try reply
    if not target_user and message.reply_to_message:
        target_user = message.reply_to_message.from_user
    
    # Validate target_user
    if not target_user or not hasattr(target_user, 'id') or target_user.id is None:
        await message.reply("Please mention a user with @ or reply to their message.\n**Usage:** `/unmute @username [reason]`")
        return
    
    reason = ' '.join(reason_parts) if reason_parts else "No reason provided"
    
    try:
        # Cancel any scheduled unmute
        await cancel_scheduled_unmute(chat.id, target_user.id)
        
        # Remove mute restrictions by setting default permissions
        await client.unban_chat_member(
            chat.id,
            target_user.id
        )
        
        # Send confirmation message
        await message.reply_text(
            f"🔊 **User Unmuted**\n"
            f"**User:** {target_user.mention}\n"
            f"**Reason:** {reason}\n"
            f"**Admin:** {message.from_user.mention}"
        )
    except UserAdminInvalid:
        await message.reply("❌ I need admin privileges to unmute users.")
    except Exception as e:
        logger.error(f"Error in unmute command: {e}")
        await message.reply(f"❌ An error occurred: {str(e)}")

def start_unmute_checker(client: Client):
    """Start the background unmute checker task."""
    asyncio.create_task(unmute_checker_task(client))