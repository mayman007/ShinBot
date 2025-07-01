import re
from datetime import datetime, timedelta
from telethon import errors
from utils.usage import save_usage

# ---------------------------
# tst command
# ---------------------------
async def tst(event):
    chat = await event.get_chat()
    await save_usage(chat, "tst")
    
    print("TST command executed")

# ---------------------------
# Mute command
# ---------------------------
async def mute_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "mute")
    
    # Check if the user has admin privileges
    sender = await event.get_sender()
    sender_id = sender.id
    
    # Check if sender has admin permissions in the chat
    try:
        participant = await event.client.get_permissions(chat.id, sender_id)
        if not (participant.is_admin or participant.is_creator):
            await event.reply("You don't have permission to use this command.")
            return
    except Exception as e:
        await event.reply(f"Error checking permissions: {str(e)}")
        return
    
    # Extract command arguments
    args = event.text.split(' ')
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
    mention_positions = []  # Track positions of mentions in the message
    
    if event.reply_to_msg_id:
        replied_msg = await event.get_reply_message()
        target_user = await replied_msg.get_sender()
    else:
        # Try to get mentioned user
        entities = event.message.entities
        if entities:
            for entity in entities:
                if hasattr(entity, 'user_id'):
                    # This handles MessageEntityMentionName (direct mention with ID)
                    target_user = await event.client.get_entity(entity.user_id)
                    mention_positions.append((entity.offset, entity.offset + entity.length))
                    break
                elif hasattr(entity, 'offset') and hasattr(entity, 'length'):
                    # This handles text mentions (@username)
                    mention_text = event.raw_text[entity.offset:entity.offset+entity.length]
                    if mention_text.startswith('@'):
                        try:
                            username = mention_text[1:]  # Remove the @ symbol
                            target_user = await event.client.get_entity(username)
                            mention_positions.append((entity.offset, entity.offset + entity.length))
                            break
                        except:
                            continue
    
    if not target_user:
        await event.reply("Please reply to a message or mention a user to mute them.")
        return
    
    # Filter out mentions from the reason
    clean_reason_parts = []
    for i, part in enumerate(reason_parts):
        # Check if this part contains a mention
        is_mention = False
        for original_pos in mention_positions:
            # Find where this part appears in the original text
            part_pos = event.raw_text.find(part)
            if part_pos >= 0:
                # Check if this part overlaps with a mention
                if (part_pos <= original_pos[1] and part_pos + len(part) >= original_pos[0]):
                    is_mention = True
                    break
        
        if not is_mention:
            clean_reason_parts.append(part)
    
    reason = "No reason provided" if not clean_reason_parts else ' '.join(clean_reason_parts)
    
    # Calculate until when the user will be muted (None for infinite)
    mute_until = None if duration is None else datetime.now() + timedelta(minutes=duration)
    
    try:
        # Apply mute restriction
        await event.client.edit_permissions(
            chat.id,
            target_user.id,
            until_date=mute_until,
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False
        )
        
        # Send confirmation message
        if duration is None:
            mute_time_str = "indefinitely"
        else:
            mute_time_str = f"for {duration} minutes" if duration != 60 else "1 hour"
            if duration < 1:
                seconds = int(duration * 60)
                mute_time_str = f"for {seconds} seconds"
        
        await event.respond(
            f"User {target_user.first_name} has been muted {mute_time_str}.\n"
            f"Reason: {reason}"
        )
    except errors.ChatAdminRequiredError:
        await event.reply("I need admin privileges to mute users.")
    except Exception as e:
        await event.reply(f"An error occurred: {str(e)}")

# ---------------------------
# Unmute command
# ---------------------------
async def unmute_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "unmute")
    
    # Check if the user has admin privileges
    sender = await event.get_sender()
    sender_id = sender.id
    
    # Check if sender has admin permissions in the chat
    try:
        participant = await event.client.get_permissions(chat.id, sender_id)
        if not (participant.is_admin or participant.is_creator):
            await event.reply("You don't have permission to use this command.")
            return
    except Exception as e:
        await event.reply(f"Error checking permissions: {str(e)}")
        return
    
    # Get target user from reply or mention
    target_user = None
    
    if event.reply_to_msg_id:
        replied_msg = await event.get_reply_message()
        target_user = await replied_msg.get_sender()
    else:
        # Try to get mentioned user
        entities = event.message.entities
        if entities:
            for entity in entities:
                if hasattr(entity, 'user_id'):
                    # This handles MessageEntityMentionName (direct mention with ID)
                    target_user = await event.client.get_entity(entity.user_id)
                    break
                elif hasattr(entity, 'offset') and hasattr(entity, 'length'):
                    # This handles text mentions (@username)
                    mention_text = event.raw_text[entity.offset:entity.offset+entity.length]
                    if mention_text.startswith('@'):
                        try:
                            username = mention_text[1:]  # Remove the @ symbol
                            target_user = await event.client.get_entity(username)
                            break
                        except:
                            continue
    
    if not target_user:
        await event.reply("Please reply to a message or mention a user to unmute them.")
        return
    
    # Remove the problematic checking code and proceed directly to unmuting
    try:
        # Remove mute restrictions
        await event.client.edit_permissions(
            chat.id,
            target_user.id,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True
        )
        
        # Send confirmation message
        await event.respond(f"User {target_user.first_name} has been unmuted.")
    except errors.ChatAdminRequiredError:
        await event.reply("I need admin privileges to unmute users.")
    except Exception as e:
        await event.reply(f"An error occurred: {str(e)}")