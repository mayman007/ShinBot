import asyncio
import datetime
import aiosqlite
import logging
from pyrogram import Client, types
from pyrogram.errors import UserAdminInvalid
from utils.usage import save_usage

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

async def check_admin_permissions(client: Client, chat_id: int, user_id: int):
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
            # Fix: Check status properly for enum values
            status_str = str(bot_member.status).lower()
            if not ('administrator' in status_str or 'creator' in status_str or 'owner' in status_str):
                logger.warning("Bot is not an admin in this chat")
        except Exception as e:
            logger.warning(f"Could not check bot admin status: {e}")
        
        # Try to get user's member status
        try:
            member = await client.get_chat_member(chat_id, user_id)
            logger.info(f"User {user_id} status: {member.status}")
            
            # Check various admin statuses - handle both string and enum values
            status_str = str(member.status).lower()
            if (member.status == 'creator' or 
                member.status == 'owner' or 
                'owner' in status_str or 
                'creator' in status_str):
                logger.info(f"User {user_id} is chat creator/owner")
                return True
            elif (member.status == 'administrator' or 
                  'administrator' in status_str or
                  'admin' in status_str):
                logger.info(f"User {user_id} is administrator")
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

async def get_target_user(client: Client, message: types.Message):
    """Extract target user from reply, mention, or username argument."""
    target_user = None
    
    # First check if replying to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    
    # Parse command arguments
    command_parts = message.text.split()
    if len(command_parts) < 2:
        return None
    
    user_identifier = command_parts[1]
    
    # Try different methods to get the user
    try:
        # Method 1: Direct username or user ID
        if user_identifier.startswith('@'):
            # Remove @ symbol
            username = user_identifier[1:]
            target_user = await client.get_users(username)
        elif user_identifier.isdigit():
            # User ID
            user_id = int(user_identifier)
            target_user = await client.get_users(user_id)
        else:
            # Try as username without @
            target_user = await client.get_users(user_identifier)
            
    except Exception as e:
        logger.warning(f"Could not get user from identifier '{user_identifier}': {e}")
        
        # Method 2: Check entities for mentions
        if message.entities:
            for entity in message.entities:
                if entity.type == "mention":
                    # Extract username from mention
                    mention_text = message.text[entity.offset:entity.offset + entity.length]
                    try:
                        target_user = await client.get_users(mention_text)
                        break
                    except Exception as e2:
                        logger.warning(f"Could not get user from mention '{mention_text}': {e2}")
                        continue
                elif entity.type == "text_mention":
                    # Direct user object from text mention
                    target_user = entity.user
                    break
    
    return target_user

# ---------------------------
# Warn command
# ---------------------------
async def warn_command(client: Client, message: types.Message):
    chat = message.chat
    sender = message.from_user
    
    logger.info(f"Warn command called by user {sender.id} ({sender.first_name}) in chat {chat.id}")
    logger.info(f"Message text: {message.text}")
    
    await save_usage(chat, "warn")
    
    # Check if the user has admin privileges
    is_admin = await check_admin_permissions(client, chat.id, sender.id)
    if not is_admin:
        logger.warning(f"Permission denied for user {sender.id} in chat {chat.id}")
        await message.reply("You don't have permission to use this command.")
        return
    
    logger.info(f"Admin check passed for user {sender.id}")
    
    # Get target user
    target_user = await get_target_user(client, message)
    
    if not target_user:
        await message.reply(
            "Please reply to a message or mention a user to warn them.\n"
            "Usage: /warn @username reason or /warn user_id reason or reply to a message with /warn reason"
        )
        return
    
    logger.info(f"Target user identified: {target_user.id} ({target_user.first_name})")
    
    # Check if trying to warn an admin
    try:
        target_member = await client.get_chat_member(chat.id, target_user.id)
        target_status = str(target_member.status).lower()
        if ('owner' in target_status or 'creator' in target_status or 
            'administrator' in target_status or 'admin' in target_status):
            await message.reply("You cannot warn administrators.")
            return
    except:
        pass
    
    # Extract reason from command
    command_parts = message.text.split(' ', 2)  # Split into max 3 parts: command, user, reason
    if len(command_parts) >= 3:
        reason = command_parts[2].strip()
    elif message.reply_to_message and len(command_parts) >= 2:
        # If replying to message, everything after command is the reason
        reason = ' '.join(command_parts[1:]).strip()
    else:
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
                    (chat.id, target_user.id, sender.id, reason, warn_date)
                )
                warn_id = cursor.lastrowid
                await connection.commit()
                logger.info(f"Warning issued: ID {warn_id} to user {target_user.id} in chat {chat.id}")
        
        # Get total warns for this user in this chat
        async with aiosqlite.connect("db/warns.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT COUNT(*) FROM warns WHERE chat_id = ? AND user_id = ? AND status = 'active'",
                    (chat.id, target_user.id)
                )
                total_warns = await cursor.fetchone()
                total_warns = total_warns[0] if total_warns else 0
        
        # Send confirmation message
        await message.reply(
            f"⚠️ Warning issued to {target_user.first_name}\n\n"
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
async def warndel_command(client: Client, message: types.Message):
    chat = message.chat
    sender = message.from_user
    
    logger.info(f"Warndel command called by user {sender.id} in chat {chat.id}")
    
    await save_usage(chat, "warndel")
    
    # Check if the user has admin privileges
    is_admin = await check_admin_permissions(client, chat.id, sender.id)
    if not is_admin:
        logger.warning(f"Permission denied for user {sender.id} in chat {chat.id}")
        await message.reply("You don't have permission to use this command.")
        return
    
    # Extract warning ID from command
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Please provide a warning ID. Usage: /warndel <warning_id>")
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
async def warnsuser_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "warnsuser")
    
    # Get target user
    target_user = await get_target_user(client, message)
    
    if not target_user:
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
                    (chat.id, target_user.id)
                )
                warnings = await cursor.fetchall()
        
        if not warnings:
            await message.reply(f"{target_user.first_name} has no active warnings in this chat.")
            return
        
        # Build response message
        lines = [f"⚠️ Warnings for {target_user.first_name}\n"]
        
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
                    current_message = f"⚠️ **Warnings for {target_user.first_name} (continued)**\n\n{lines[i]}"
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
async def warnslist_command(client: Client, message: types.Message):
    chat = message.chat
    sender = message.from_user
    
    logger.info(f"Warnslist command called by user {sender.id} in chat {chat.id}")
    
    await save_usage(chat, "warnslist")
    
    # Check if the user has admin privileges
    is_admin = await check_admin_permissions(client, chat.id, sender.id)
    if not is_admin:
        logger.warning(f"Permission denied for user {sender.id} in chat {chat.id}")
        await message.reply("You don't have permission to use this command.")
        return
    
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
