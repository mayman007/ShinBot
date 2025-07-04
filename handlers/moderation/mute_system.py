import re
import asyncio
import aiosqlite
import logging
from datetime import datetime, timedelta
from pyrogram import Client, types
from pyrogram.errors import UserAdminInvalid
from utils.usage import save_usage
from utils.decorators import admin_only
from utils.helpers import extract_user_and_reason

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

# ---------------------------
# Mute command
# ---------------------------
@admin_only
async def mute_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "mute")
    
    # Extract command arguments
    args = message.text.split(' ')
    duration = None  # Default: infinite mute
    reason_parts = []
    time_found = False
    
    # Parse all arguments to find time duration (format: 1h, 30m, 10s etc.)
    for i in range(1, len(args)):
        arg = args[i].lower()
        time_match = re.match(r'^(\d+)([hmds])$', arg)
        if time_match and not time_found:
            time_found = True
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
            reason_parts.append(args[i])
    
    # Get target user and reason using helper function
    target_user, helper_reason = await extract_user_and_reason(client, message)
    
    # Use helper reason if no reason found in time parsing, otherwise use parsed reason
    if not reason_parts and helper_reason:
        reason = helper_reason
    elif reason_parts:
        reason = ' '.join(reason_parts)
    else:
        reason = "No reason provided"
    
    if not target_user:
        await message.reply("Please reply to a message or mention a user to mute them.\n**Usage:** `/mute @username [time] [reason]` or reply to a message with `/mute [time] [reason]`")
        return
    
    # Calculate until when the user will be muted (None for infinite)
    mute_until = None if duration is None else datetime.now() + timedelta(minutes=duration)
    
    try:
        # Apply mute restriction
        await client.restrict_chat_member(
            chat.id,
            target_user.id,
            types.ChatPermissions(), # No permissions
            until_date=mute_until
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
        await message.reply(f"❌ An error occurred: {str(e)}")

# ---------------------------
# Unmute command
# ---------------------------
@admin_only
async def unmute_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "unmute")
    
    # Get target user and reason using helper function
    target_user, reason = await extract_user_and_reason(client, message)
    
    if not target_user:
        await message.reply("Please reply to a message or mention a user to unmute them.\n**Usage:** `/unmute @username [reason]` or reply to a message with `/unmute [reason]`")
        return
    
    if not reason:
        reason = "No reason provided"
    
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
        await message.reply(f"❌ An error occurred: {str(e)}")

def start_unmute_checker(client: Client):
    """Start the background unmute checker task."""
    asyncio.create_task(unmute_checker_task(client))