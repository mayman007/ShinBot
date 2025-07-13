import datetime
import time
import math
import re
import asyncio
from pyrogram import Client, types
from tcp_latency import measure_latency
from utils.usage import save_usage
from utils.helpers import extract_user_and_reason

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
    
    # Check if user wants moderation commands only
    args = message.text.split()
    if len(args) > 1 and args[1].lower() == "mod":
        mod_help_text = (
            "\nHere's my moderation commands list:\n"
            "/ban - Ban a user\n"
            "/demote - Demote a user from admin\n"
            "/kick - Kick a user\n"
            "/mute - Mute a user\n"
            "/promote - Promote a user to admin\n"
            "/unban - Unban a user\n"
            "/unmute - Unmute a user\n"
            "/warn - Issue a warning to a user\n"
            "/warndel - Delete a warning by ID\n"
            "/warnslist - List all active warnings in chat\n"
            "/warnsuser - View warnings for a specific user\n"
        )
        await message.reply(mod_help_text)
        return
    
    help_text = (
        "\nHere's my commands list:\n"
        "/advice - Get a random advice\n"
        "/affirmation - Get a random affirmation\n"
        "/aghpb - Anime girl holding programming book\n"
        "/anime - Search Anime\n"
        "/ban - Ban a user\n"
        "/calc - Calculate mathematical expressions\n"
        "/character - Search Anime & Manga characters\n"
        "/chatid - Get the current chat ID\n"
        "/choose - Make me choose for you\n"
        "/coinflip - Flip a coin\n"
        "/dadjoke - Get a random dad joke\n"
        "/demote - Demote a user from admin\n"
        "/dog - Get a random dog pic/vid/gif\n"
        "/echo - Repeats your words\n"
        "/geekjoke - Get a random geek joke\n"
        "/gemini - Chat with Google's Gemini Pro AI\n"
        "/groupinfo - Get group's info\n"
        "/help - This message\n"
        "/imagine - Generate AI images\n"
        "/joindate - Get each member's join date in the group\n"
        "/kick - Kick a user\n"
        "/manga - Search Manga\n"
        "/meme - Get a random meme from Reddit\n"
        "/mute - Mute a user\n"
        "/pfp - Get user's profile picture\n"
        "/ping - Get bot's latency\n"
        "/promote - Promote a user to admin\n"
        "/reverse - Reverse your words\n"
        "/rps - Play Rock Paper Scissors\n"
        "/slot - A slot game\n"
        "/start - Bot's introduction\n"
        "/timer - Set yourself a timer\n"
        "/timerdel - Delete a timer\n"
        "/timerslist - Get a list of timers set in this chat\n"
        "/unban - Unban a user\n"
        "/unmute - Unmute a user\n"
        "/warn - Issue a warning to a user\n"
        "/warndel - Delete a warning by ID\n"
        "/warnslist - List all active warnings in chat\n"
        "/warnsuser - View warnings for a specific user\n"
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
# Calculator command
# ---------------------------
async def calc_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "calc")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /calc <expression>\nExample: /calc 2 + 2 * 3\nSupports: +, -, *, /, %, ^ (power), ! (factorial), sin, cos, tan, log, sqrt, pi, e")
        return
    
    expression = args[1].strip()
    
    # Limit expression length to prevent abuse
    if len(expression) > 200:
        await message.reply("Error: Expression too long (max 200 characters)")
        return
    
    try:
        # Check for factorial abuse before processing
        factorial_matches = re.findall(r'(\d+)!', expression)
        for match in factorial_matches:
            if int(match) > 20:
                await message.reply("Error: Factorial input too large (max 20!)")
                return
        
        # Replace ^ with ** for exponentiation
        expression = re.sub(r'\^', '**', expression)
        
        # Replace factorial notation (e.g., 5! becomes math.factorial(5))
        expression = re.sub(r'(\d+)!', r'math.factorial(\1)', expression)
        
        # Replace common math functions with math module equivalents
        expression = re.sub(r'\bsin\b', 'math.sin', expression)
        expression = re.sub(r'\bcos\b', 'math.cos', expression)
        expression = re.sub(r'\btan\b', 'math.tan', expression)
        expression = re.sub(r'\blog\b', 'math.log', expression)
        expression = re.sub(r'\bsqrt\b', 'math.sqrt', expression)
        expression = re.sub(r'\bpi\b', 'math.pi', expression)
        expression = re.sub(r'\be\b', 'math.e', expression)
        
        # Use eval with restricted globals for safety
        allowed_names = {
            "__builtins__": {},
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
        }
        
        # Use asyncio timeout for cross-platform compatibility
        async def evaluate_expression():
            return eval(expression, allowed_names, {})
        
        try:
            result = await asyncio.wait_for(evaluate_expression(), timeout=5.0)
        except asyncio.TimeoutError:
            await message.reply("Error: Calculation timeout (too complex)")
            return
        
        # Check if result is too large
        if isinstance(result, (int, float)) and abs(result) > 1e15:
            await message.reply("Error: Result too large to display")
            return
        
        # Format the result nicely
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)
        
        await message.reply(f"**Expression:** `{args[1]}`\n**Result:** `{result}`")
        
    except ZeroDivisionError:
        await message.reply("Error: Division by zero!")
    except (SyntaxError, NameError, TypeError, ValueError) as e:
        await message.reply(f"Error: Invalid expression. {str(e)}")
    except Exception as e:
        await message.reply(f"Error: {str(e)}")

# ---------------------------
# Profile Picture command
# ---------------------------
async def pfp_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "pfp")
    
    # Get target user using helper function
    user, _ = await extract_user_and_reason(client, message)
    
    # If no user found from helper, use message sender as fallback
    if not user:
        user = message.from_user
    
    if not user:
        await message.reply("Error: No user found.")
        return
    
    try:
        # First try to get the user's full info which includes profile photo
        user_full = await client.get_users(user.id)
        
        # Check if user has a profile photo
        if not user_full.photo:
            await message.reply(f"{user_full.first_name} doesn't have a profile picture or it's not accessible.")
            return
        
        # Try to download and send the profile photo
        try:
            # Get the profile photo file
            photo_file = await client.download_media(user_full.photo.big_file_id, in_memory=True)
            
            # Send the photo
            await message.reply_photo(
                photo_file,
                caption=f"Profile picture of {user_full.first_name}"
            )
            
        except Exception as download_error:
            # Fallback: try using get_chat_photos
            try:
                photos = [photo async for photo in client.get_chat_photos(user.id)]
                
                if not photos:
                    await message.reply(f"{user_full.first_name} doesn't have a profile picture or it's not accessible.")
                    return
                
                # Send the latest profile photo
                await message.reply_photo(
                    photos[0].file_id,
                    caption=f"Profile picture of {user_full.first_name}"
                )
                
            except Exception as fallback_error:
                await message.reply(f"Error: Unable to access {user_full.first_name}'s profile picture. This might be due to privacy settings.")
        
    except Exception as e:
        await message.reply(f"Error retrieving user information: {str(e)}")

# ---------------------------
# Chat ID command
# ---------------------------
async def chatid_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "chatid")
    await message.reply(f"Chat ID: `{chat.id}`")