import datetime
import time
from pyrogram import Client, types
from tcp_latency import measure_latency
from utils.usage import save_usage

# ---------------------------
# Start command
# ---------------------------
async def start_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "start")
    sender = message.from_user
    await message.reply(
        f"Hello {sender.first_name}, My name is Shin and I'm developed by @Mayman007tg.\n"
        "I'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me."
    )

# ---------------------------
# Help command
# ---------------------------
async def help_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "help")
    help_text = (
        "\nHere's my commands list:\n"
        "/advice - Get a random advice\n"
        "/affirmation - Get a random affirmation\n"
        "/aghpb - Anime girl holding programming book\n"
        "/anime - Search Anime\n"
        "/character - Search Anime & Manga characters\n"
        "/chatid - Get the current chat ID\n"
        "/choose - Make me choose for you\n"
        "/coinflip - Flip a coin\n"
        "/dadjoke - Get a random dad joke\n"
        "/dog - Get a random dog pic/vid/gif\n"
        "/echo - Repeats your words\n"
        "/geekjoke - Get a random geek joke\n"
        "/gemini - Chat with Google's Gemini Pro AI\n"
        "/help - This message\n"
        "/imagine - Generate AI images\n"
        "/joindate - Get each member's join date in the group\n"
        "/manga - Search Manga\n"
        "/meme - Get a random meme from Reddit\n"
        "/pfp - Get user's profile picture\n"
        "/ping - Get bot's latency\n"
        "/reverse - Reverse your words\n"
        "/slot - A slot game\n"
        "/start - Bot's introduction\n"
        "/timer - Set yourself a timer\n"
        "/timerdel - Delete a timer\n"
        "/timerslist - Get a list of timers set in this chat\n"
        "/yt - Download videos from YouTube and other sites\n"
    )
    await message.reply(help_text)

# ---------------------------
# Joindate command
# ---------------------------
async def list_join_dates(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "joindate")
    # This command must be used in a group or supergroup.
    if str(chat.type) not in ["ChatType.SUPERGROUP", "ChatType.GROUP"]:
        await message.reply(f"This command can only be used in groups. Current chat type: {chat.type}")
        return

    # Check bot's admin permissions
    try:
        me = await client.get_me()
        perms = await client.get_chat_member(chat.id, me.id)
        
        # Check if bot has admin permissions
        bot_status = str(perms.status) if hasattr(perms, 'status') else str(perms)
        allowed_statuses = ['ChatMemberStatus.ADMINISTRATOR', 'ChatMemberStatus.CREATOR', 'administrator', 'creator']
        
        if not any(status in bot_status for status in allowed_statuses):
            await message.reply(f"Error: Bot doesn't have the necessary admin permissions. Current status: {bot_status}")
            return
            
    except Exception as e:
        await message.reply(f"Error: Unable to fetch bot permissions. Error: {str(e)}")
        return

    # Determine if a specific member is targeted (by reply or argument)
    target_user = None
    if message.reply_to_message:
        try:
            target_user = message.reply_to_message.from_user.id
        except Exception:
            pass
    else:
        args = message.text.split()
        if len(args) > 1:
            arg = args[1].strip()
            # If the identifier starts with '@', remove it.
            if arg.startswith('@'):
                arg = arg[1:]
            # Try to interpret the argument as an integer user ID.
            try:
                target_user = int(arg)
            except ValueError:
                try:
                    # Fallback: resolve using get_users
                    entity = await client.get_users(arg)
                    target_user = entity.id
                except Exception:
                    await message.reply("Error: Unable to find a user with the provided identifier.")
                    return

    if target_user is not None:
        # Get specific user's details
        try:
            participant = await client.get_chat_member(chat.id, target_user)
            user = participant.user
            
            join_date = "Not Available"
            if hasattr(participant, 'joined_date') and participant.joined_date:
                join_date = participant.joined_date.strftime('%Y-%m-%d %H:%M:%S')
            
            name = user.first_name or ""
            if user.last_name:
                name += " " + user.last_name
            result = f"Name: {name}\nID: {user.id}\nJoin Date: {join_date}"
            await message.reply(result)
        except Exception:
            await message.reply("Error: Unable to retrieve the specified user's details.")
            return
    else:
        # Get all members and their join dates
        members = []
        async for member in client.get_chat_members(chat.id):
            user = member.user
            join_date = None
            if hasattr(member, 'joined_date') and member.joined_date:
                join_date = member.joined_date
                join_date_str = join_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                join_date_str = "Not Available"
            
            name = user.first_name or ""
            if user.last_name:
                name += " " + user.last_name
            if len(name) > 20:
                name = name[:17] + "..."
            
            members.append({
                'name': name,
                'id': user.id,
                'join_date': join_date,
                'join_date_str': join_date_str
            })

        # Sort members by join date
        members.sort(key=lambda m: m['join_date'] if m['join_date'] is not None else datetime.datetime.max)

        # Build formatted output
        output_lines = []
        for m in members:
            output_lines.append(f"Name: {m['name']}")
            output_lines.append(f"ID: {m['id']}")
            output_lines.append(f"Join Date: {m['join_date_str']}")
            output_lines.append("-" * 30)
        output_lines.append(f"Total Members: {len(members)}")
        output = "\n".join(output_lines)
        await message.reply(output)

# ---------------------------
# Ping Command Handler
# ---------------------------
async def ping_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "ping")
    
    try:
        initial_latency = measure_latency(host='telegram.org')
        if not initial_latency or len(initial_latency) == 0:
            initial_latency_ms = "Failed to measure"
        else:
            initial_latency_ms = f"{int(initial_latency[0])}ms"
            
        start_time = time.time()
        sent_message = await message.reply("...")
        end_time = time.time()
        round_latency = int((end_time - start_time) * 1000)
        await sent_message.edit_text(
            f"Pong!\nInitial response: `{initial_latency_ms}`\nRound-trip: `{round_latency}ms`"
        )
    except Exception as e:
        await message.reply(f"Error measuring latency: {str(e)}")

# ---------------------------
# Profile Picture command
# ---------------------------
async def pfp_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "pfp")
    
    # Determine target user (reply, argument, or sender)
    target_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
    else:
        args = message.text.split()
        if len(args) > 1:
            arg = args[1].strip()
            # Remove '@' if present
            if arg.startswith('@'):
                arg = arg[1:]
            try:
                # Try as user ID first
                user_id = int(arg)
                target_user = await client.get_users(user_id)
            except ValueError:
                try:
                    # Try as username
                    target_user = await client.get_users(arg)
                except Exception:
                    await message.reply("Error: Unable to find a user with the provided identifier.")
                    return
        else:
            # Use message sender
            target_user = message.from_user
    
    if not target_user:
        await message.reply("Error: No user found.")
        return
    
    try:
        # Get user's profile photos
        photos = [photo async for photo in client.get_chat_photos(target_user.id)]
        
        if not photos:
            await message.reply(f"{target_user.first_name} doesn't have a profile picture.")
            return
        
        # Send the latest profile photo
        await message.reply_photo(
            photos[0].file_id,
            caption=f"Profile picture of {target_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"Error retrieving profile picture: {str(e)}")

# ---------------------------
# Chat ID command
# ---------------------------
async def chatid_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "chatid")
    await message.reply(f"Chat ID: `{chat.id}`")

