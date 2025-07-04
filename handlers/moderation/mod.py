import re
from datetime import datetime, timedelta
from pyrogram import Client, types
from pyrogram.errors import UserAdminInvalid
from utils.usage import save_usage


# ---------------------------
# Mute command
# ---------------------------
async def mute_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "mute")
    
    # Check if the user has admin privileges
    sender = message.from_user
    
    # Check if sender has admin permissions in the chat
    try:
        member = await client.get_chat_member(chat.id, sender.id)
        if member.status not in ('administrator', 'creator'):
            await message.reply("You don't have permission to use this command.")
            return
    except Exception as e:
        await message.reply(f"Error checking permissions: {str(e)}")
        return
    
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
    
    # Get reason if provided
    reason = "No reason provided" if not reason_parts else ' '.join(reason_parts)
    
    # Get target user from reply or mention
    target_user = None
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        # Try to get mentioned user
        entities = message.entities
        if entities:
            for entity in entities:
                if entity.type == 'mention':
                    mention_text = message.text[entity.offset:entity.offset+entity.length]
                    try:
                        target_user = await client.get_users(mention_text)
                        break
                    except:
                        continue
                elif entity.type == 'text_mention':
                    target_user = entity.user
                    break
    
    if not target_user:
        await message.reply("Please reply to a message or mention a user to mute them.")
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
        
        # Send confirmation message
        if duration is None:
            mute_time_str = "indefinitely"
        else:
            mute_time_str = f"for {duration} minutes" if duration != 60 else "1 hour"
            if duration < 1:
                seconds = int(duration * 60)
                mute_time_str = f"for {seconds} seconds"
        
        await message.reply_text(
            f"User {target_user.first_name} has been muted {mute_time_str}.\n"
            f"Reason: {reason}"
        )
    except UserAdminInvalid:
        await message.reply("I need admin privileges to mute users.")
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")

# ---------------------------
# Unmute command
# ---------------------------
async def unmute_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "unmute")
    
    # Check if the user has admin privileges
    sender = message.from_user
    
    # Check if sender has admin permissions in the chat
    try:
        member = await client.get_chat_member(chat.id, sender.id)
        if member.status not in ('administrator', 'creator'):
            await message.reply("You don't have permission to use this command.")
            return
    except Exception as e:
        await message.reply(f"Error checking permissions: {str(e)}")
        return
    
    # Get target user from reply or mention
    target_user = None
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        # Try to get mentioned user
        entities = message.entities
        if entities:
            for entity in entities:
                if entity.type == 'mention':
                    mention_text = message.text[entity.offset:entity.offset+entity.length]
                    try:
                        target_user = await client.get_users(mention_text)
                        break
                    except:
                        continue
                elif entity.type == 'text_mention':
                    target_user = entity.user
                    break
    
    if not target_user:
        await message.reply("Please reply to a message or mention a user to unmute them.")
        return
    
    # Remove the problematic checking code and proceed directly to unmuting
    try:
        # Remove mute restrictions by setting default permissions
        await client.unban_chat_member(
            chat.id,
            target_user.id
        )
        
        # Send confirmation message
        await message.reply_text(f"User {target_user.first_name} has been unmuted.")
    except UserAdminInvalid:
        await message.reply("I need admin privileges to unmute users.")
    except Exception as e:
        await message.reply(f"An error occurred: {str(e)}")