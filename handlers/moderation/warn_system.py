import asyncio
import datetime
import aiosqlite
import logging
from pyrogram import Client, types
from pyrogram.errors import UserAdminInvalid
from utils.usage import save_usage
from utils.decorators import admin_only, check_admin_permissions
from utils.helpers import extract_user_and_reason

logger = logging.getLogger(__name__)

async def init_warns_db():
    """Initialize the warns database."""
    async with aiosqlite.connect("db/warns.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS warns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    user_id INTEGER,
                    warned_by INTEGER,
                    reason TEXT,
                    warn_date TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            await connection.commit()
            logger.info("Warns database initialized")

# ---------------------------
# Warn command
# ---------------------------
@admin_only
async def warn_command(client: Client, message: types.Message):
    chat = message.chat
    sender = message.from_user
    
    logger.info(f"Warn command called by user {sender.id} ({sender.first_name}) in chat {chat.id}")
    logger.info(f"Message text: {message.text}")
    
    await save_usage(chat, "warn")
    
    # Get target user using helper function
    user, reason = await extract_user_and_reason(client, message)
    
    if not user:
        await message.reply(
            "Please reply to a message or mention a user to warn them.\n"
            "Usage: /warn @username reason or /warn user_id reason or reply to a message with /warn reason"
        )
        return
    
    logger.info(f"Target user identified: {user.id} ({user.first_name})")
    
    # Use reason from helper function or default
    if not reason or reason.strip() == "":
        reason = "No reason provided"
    
    # Check if reason exceeds max length
    if len(reason) > 500:
        await message.reply("Reason is too long! Please limit to 500 characters.")
        return
    
    try:
        # Initialize database
        await init_warns_db()
        
        # Save warn to database
        warn_date = datetime.datetime.now().isoformat()
        async with aiosqlite.connect("db/warns.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO warns (chat_id, user_id, warned_by, reason, warn_date) VALUES (?, ?, ?, ?, ?)",
                    (chat.id, user.id, sender.id, reason, warn_date)
                )
                warn_id = cursor.lastrowid
                await connection.commit()
                logger.info(f"Warning issued: ID {warn_id} to user {user.id} in chat {chat.id}")
        
        # Get total warns for this user in this chat
        async with aiosqlite.connect("db/warns.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT COUNT(*) FROM warns WHERE chat_id = ? AND user_id = ? AND status = 'active'",
                    (chat.id, user.id)
                )
                total_warns = await cursor.fetchone()
                total_warns = total_warns[0] if total_warns else 0
        
        # Send confirmation message
        await message.reply(
            f"⚠️ Warning issued to {user.first_name}\n\n"
            f"Warning ID: #{warn_id}\n"
            f"Reason: {reason}\n"
            f"Total warnings: {total_warns}\n"
            f"Issued by: {sender.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"An error occurred while issuing the warning: {str(e)}")
        logger.error(f"Error in warn command: {e}")

# ---------------------------
# Warning delete command
# ---------------------------
@admin_only
async def warndel_command(client: Client, message: types.Message):
    chat = message.chat
    sender = message.from_user
    
    logger.info(f"Warndel command called by user {sender.id} in chat {chat.id}")
    
    await save_usage(chat, "warndel")
    
    # Extract warning ID from command
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Please provide a warning ID. Usage: `/warndel [ID]`\nSee warnings IDs from `/warnslist` or `/warnsuser @user`")
        return
    
    try:
        warn_id = int(args[1])
    except ValueError:
        await message.reply("Invalid warning ID. Please provide a numeric ID.")
        return
    
    try:
        await init_warns_db()
        
        # Check if warning exists and is in this chat
        async with aiosqlite.connect("db/warns.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT user_id, reason, status FROM warns WHERE id = ? AND chat_id = ?",
                    (warn_id, chat.id)
                )
                warning = await cursor.fetchone()
                
                if not warning:
                    await message.reply(f"Warning #{warn_id} not found in this chat.")
                    return
                
                if warning[2] == 'deleted':
                    await message.reply(f"Warning #{warn_id} has already been deleted.")
                    return
                
                # Mark warning as deleted
                await cursor.execute(
                    "UPDATE warns SET status = 'deleted' WHERE id = ?",
                    (warn_id,)
                )
                await connection.commit()
                logger.info(f"Warning deleted: ID {warn_id} by admin {sender.id}")
        
        # Get user info
        try:
            warned_user = await client.get_users(warning[0])
            user_name = warned_user.first_name
        except:
            user_name = f"User {warning[0]}"
        
        await message.reply(
            f"✅ Warning #{warn_id} has been deleted\n\n"
            f"User: {user_name}\n"
            f"Reason: {warning[1]}\n"
            f"Deleted by: {sender.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"An error occurred while deleting the warning: {str(e)}")
        logger.error(f"Error in warndel command: {e}")

# ---------------------------
# User warnings command
# ---------------------------
@admin_only
async def warnsuser_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "warnsuser")
    
    # Get target user using helper function
    user, _ = await extract_user_and_reason(client, message)
    
    if not user:
        await message.reply(
            "Please reply to a message or mention a user to view their warnings.\n"
            "Usage: /warnsuser @username or /warnsuser user_id or reply to a message with /warnsuser"
        )
        return
    
    try:
        await init_warns_db()
        
        # Get all active warnings for the user in this chat
        async with aiosqlite.connect("db/warns.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, warned_by, reason, warn_date FROM warns WHERE chat_id = ? AND user_id = ? AND status = 'active' ORDER BY warn_date DESC",
                    (chat.id, user.id)
                )
                warnings = await cursor.fetchall()
        
        if not warnings:
            await message.reply(f"{user.first_name} has no active warnings in this chat.")
            return
        
        # Build response message
        lines = [f"⚠️ Warnings for {user.first_name}\n"]
        
        for warn_id, warned_by, reason, warn_date in warnings:
            # Format date
            try:
                date_obj = datetime.datetime.fromisoformat(warn_date)
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
            except:
                formatted_date = warn_date
            
            # Get admin info
            try:
                admin_user = await client.get_users(warned_by)
                admin_name = admin_user.first_name
            except:
                admin_name = f"Admin {warned_by}"
            
            lines.append(
                f"#{warn_id} - {formatted_date}\n"
                f"Reason: {reason}\n"
                f"By: {admin_name}\n"
            )
        
        lines.append(f"\nTotal active warnings: {len(warnings)}")
        
        # Handle message length limit
        full_message = "\n".join(lines)
        if len(full_message) <= 4000:
            await message.reply(full_message)
        else:
            # Split into multiple messages
            messages = []
            current_message = lines[0]
            
            for i in range(1, len(lines)):
                if len(current_message) + len(lines[i]) + 2 > 4000:
                    messages.append(current_message)
                    current_message = f"⚠️ **Warnings for {user.first_name} (continued)**\n\n{lines[i]}"
                else:
                    current_message += "\n" + lines[i]
            
            messages.append(current_message)
            
            for msg in messages:
                await message.reply(msg)
                await asyncio.sleep(0.5)
        
    except Exception as e:
        await message.reply(f"An error occurred while fetching warnings: {str(e)}")
        logger.error(f"Error in warnsuser command: {e}")

# ---------------------------
# List all warnings command
# ---------------------------
@admin_only
async def warnslist_command(client: Client, message: types.Message):
    chat = message.chat
    sender = message.from_user
    
    logger.info(f"Warnslist command called by user {sender.id} in chat {chat.id}")
    
    await save_usage(chat, "warnslist")
    
    try:
        await init_warns_db()
        
        # Get all active warnings in this chat
        async with aiosqlite.connect("db/warns.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT id, user_id, warned_by, reason, warn_date FROM warns WHERE chat_id = ? AND status = 'active' ORDER BY warn_date DESC",
                    (chat.id,)
                )
                warnings = await cursor.fetchall()
        
        if not warnings:
            await message.reply("No active warnings in this chat.")
            return
        
        # Group warnings by user
        user_warnings = {}
        for warn_id, user_id, warned_by, reason, warn_date in warnings:
            if user_id not in user_warnings:
                user_warnings[user_id] = []
            user_warnings[user_id].append((warn_id, warned_by, reason, warn_date))
        
        # Build response message
        lines = [f"⚠️ All Active Warnings in {chat.title or 'this chat'}\n"]
        
        for user_id, user_warns in user_warnings.items():
            # Get user info
            try:
                user = await client.get_users(user_id)
                user_name = user.first_name
            except:
                user_name = f"User {user_id}"
            
            lines.append(f"👤 {user_name} ({len(user_warns)} warnings):")
            
            for warn_id, warned_by, reason, warn_date in user_warns[:3]:  # Show max 3 per user
                # Format date
                try:
                    date_obj = datetime.datetime.fromisoformat(warn_date)
                    formatted_date = date_obj.strftime("%m-%d %H:%M")
                except:
                    formatted_date = warn_date
                
                # Get admin info
                try:
                    admin_user = await client.get_users(warned_by)
                    admin_name = admin_user.first_name
                except:
                    admin_name = f"Admin {warned_by}"
                
                short_reason = reason[:50] + "..." if len(reason) > 50 else reason
                lines.append(f"  #{warn_id} - {formatted_date} by {admin_name}: {short_reason}")
            
            if len(user_warns) > 3:
                lines.append(f"  ... and {len(user_warns) - 3} more")
            
            lines.append("")
        
        lines.append(f"Total warnings: {len(warnings)}")
        lines.append("Use /warnsuser @user for detailed user warnings")
        
        # Handle message length limit
        full_message = "\n".join(lines)
        if len(full_message) <= 4000:
            await message.reply(full_message)
        else:
            # Split into multiple messages
            messages = []
            current_message = lines[0]
            
            for i in range(1, len(lines)):
                if len(current_message) + len(lines[i]) + 2 > 4000:
                    messages.append(current_message)
                    current_message = f"⚠️ **All Active Warnings (continued)**\n\n{lines[i]}"
                else:
                    current_message += "\n" + lines[i]
            
            messages.append(current_message)
            
            for msg in messages:
                await message.reply(msg)
                await asyncio.sleep(0.5)
        
    except Exception as e:
        await message.reply(f"An error occurred while fetching warnings: {str(e)}")
        logger.error(f"Error in warnslist command: {e}")
        