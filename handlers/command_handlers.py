import asyncio
import datetime
import io
import aiohttp
import aiosqlite
import random
import time
import praw
import google.generativeai as genai
from tcp_latency import measure_latency
from telethon import Button
from config import BOT_USERNAME, ADMIN_ID, GEMINI_API_KEY, HUGGINGFACE_TOKEN, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from utils.usage import save_usage
from utils.timer_scheduler import check_pending_timers, schedule_timer, init_timer_db

# ---------------------------
# Usagedata command
# ---------------------------
async def usagedata_command(event):
    # Check if sender is admin
    if event.sender_id == int(ADMIN_ID):
        data_message = "Here is all the usage data!\n"
        async with aiosqlite.connect("db/usage.db") as connection:
            async with connection.cursor() as cursor:
                data = await cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = await data.fetchall()
                for table in tables:
                    table_name = table[0]
                    data_message += "===================\n\n"
                    data_message += f"**{table_name}**\n"
                    data = await cursor.execute(f"SELECT * FROM {table_name};")
                    rows = await data.fetchall()
                    for row in rows:
                        data_message += (
                            f"- Chat ID: {row[0]}\n"
                            f"- Chat Name: **{row[1]}**\n"
                            f"- Usage Count: **{row[2]}**\n"
                            f"- Chat Type: {row[3]}\n"
                        )
                        # Check if row has enough elements before accessing them
                        if len(row) > 4:
                            data_message += f"- Chat Members: {row[4]}\n"
                        if len(row) > 5:
                            data_message += f"- Chat Invite: {row[5]}\n"
                        data_message += "\n"
        limit = 3800
        if len(data_message) > limit:
            parts = [data_message[i: i + limit] for i in range(0, len(data_message), limit)]
            for part in parts:
                await event.reply(part)
                await asyncio.sleep(0.5)
        else:
            await event.reply(data_message)
    else:
        await event.reply("You're not allowed to use this command")

# ---------------------------
# Start command
# ---------------------------
async def start_command(event):
    sender = await event.get_sender()
    await event.reply(
        f"Hello {sender.first_name}, My name is Shin and I'm developed by @Mayman007tg.\n"
        "I'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me."
    )

# ---------------------------
# Help command
# ---------------------------
async def help_command(event):
    help_text = (
        "\nHere's my commands list:\n"
        "/advice - Get a random advice\n"
        "/affirmation - Get a random affirmation\n"
        "/aghpb - Anime girl holding programming book\n"
        "/anime - Search Anime\n"
        "/character - Search Anime & Manga characters\n"
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
        "/ping - Get bot's latency\n"
        "/reverse - Reverse your words\n"
        "/slot - A slot game\n"
        "/start - Bot's introduction\n"
        "/timerslist - Get a list of timers set in this chat\n"
        "/timer - Set yourself a timer\n"
        "/yt - Download videos from YouTube and other sites\n"
    )
    await event.reply(help_text)

# ---------------------------
# Joindate command
# ---------------------------
async def list_join_dates(event):
    chat = await event.get_chat()
    await save_usage(chat, "joindate")
    # This command must be used in a group or supergroup.
    if not event.is_group:
        await event.reply("This command can only be used in groups.")
        return

    # Check bot's admin permissions using event.client.get_permissions
    try:
        me = await event.client.get_me()
        perms = await event.client.get_permissions(event.chat_id, me.id)
    except Exception:
        await event.reply("Error: Unable to fetch bot permissions. Ensure the bot is added to the group.")
        return

    if not (perms and getattr(perms, 'is_admin', False)):
        await event.reply("Error: Bot doesn't have the necessary admin permissions. Please add it as an admin.")
        return

    # Determine if a specific member is targeted (by reply or argument)
    target_user = None
    if event.is_reply:
        try:
            reply = await event.get_reply_message()
            target_user = reply.sender_id
        except Exception:
            pass
    else:
        args = event.message.message.split()
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
                    # Fallback: resolve using get_entity
                    entity = await event.client.get_entity(arg)
                    target_user = entity.id
                except Exception:
                    await event.reply("Error: Unable to find a user with the provided identifier.")
                    return

    if target_user is not None:
        # Instead of using get_participant, iterate over participants to locate the target
        participant = None
        async for user in event.client.iter_participants(event.chat_id):
            if user.id == target_user:
                participant = user
                break
        if not participant:
            await event.reply("Error: Unable to retrieve the specified user's details.")
            return

        join_date = "Not Available"
        if hasattr(participant, 'participant') and getattr(participant.participant, 'date', None):
            join_date = participant.participant.date.strftime('%Y-%m-%d %H:%M:%S')
        name = participant.first_name or ""
        if participant.last_name:
            name += " " + participant.last_name
        result = f"Name: {name}\nID: {participant.id}\nJoin Date: {join_date}"
        await event.reply(result)
    else:
        # Otherwise, iterate over all members and collect their join dates.
        members = []
        async for user in event.client.iter_participants(event.chat_id):
            join_date = None
            if hasattr(user, 'participant') and getattr(user.participant, 'date', None):
                join_date = user.participant.date
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
                'join_date': join_date,  # datetime or None
                'join_date_str': join_date_str
            })

        # Sort members: those with a join_date first (earliest first), then those without join dates.
        members.sort(key=lambda m: m['join_date'].replace(tzinfo=None)
                    if m['join_date'] is not None else datetime.datetime.max)

        # Build a mobile-friendly formatted output.
        output_lines = []
        for m in members:
            output_lines.append(f"Name: {m['name']}")
            output_lines.append(f"ID: {m['id']}")
            output_lines.append(f"Join Date: {m['join_date_str']}")
            output_lines.append("-" * 30)
        output_lines.append(f"Total Members: {len(members)}")
        output = "\n".join(output_lines)
        await event.reply(output)

# ---------------------------
# Character Command Handler
# ---------------------------
async def character_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "character")
    
    # Remove command from text and get query
    parts = event.message.message.split()
    if len(parts) < 2:
        await event.reply("Please provide a search query.")
        return
    query = " ".join(parts[1:])
    
    index = 0
    character_results_list = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://api.jikan.moe/v4/characters?q={query}&order_by=favorites&sort=desc") as response:
                if response.status == 200:
                    results = await response.json()
                else:
                    await event.reply(f"API Error: Status {response.status}")
                    return
                
            for result in results.get('data', []):
                this_result = {
                    'url': result["url"],
                    'image_url': result["images"]["jpg"]["image_url"],
                    'name': result["name"],
                    'favorites': result["favorites"],
                    'about': "" if result["about"] is None else (
                        result["about"][:800] + "..." if len(result["about"]) > 800 else result["about"]
                    )
                }
                character_results_list.append(this_result)
                index += 1
                if index == 10:
                    break
        except Exception as e:
            await event.reply(f"Error fetching data: {str(e)}")
            return

    if index == 0:
        await event.reply("No results found.")
        return

    try:
        buttons = [[Button.url("Open in MAL", character_results_list[0]['url'])]]
        msg = await event.client.send_file(
            chat.id,
            character_results_list[0]['image_url'],
            caption=(
                f"**🎗️ Name:** {character_results_list[0]['name']}\n"
                f"**⭐ Favorites:** {character_results_list[0]['favorites']}\n"
                f"**👓 About:** {character_results_list[0]['about']}"
            ),
            buttons=buttons
        )

        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "CREATE TABLE IF NOT EXISTS character (message_id TEXT, current_index INTEGER, character_result_list TEXT)"
                )
                await cursor.execute(
                    "INSERT INTO character (message_id, current_index, character_result_list) VALUES (?, ?, ?)",
                    (str(msg.id), 0, str(character_results_list))
                )
                await connection.commit()
    except Exception as e:
        await event.reply(f"Error displaying results: {str(e)}")

# ---------------------------
# Manga Command Handler
# ---------------------------
async def manga_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "manga")
    
    text = event.message.message
    query = text.replace("/manga", "").replace(f"@{BOT_USERNAME}", "").strip()
    if not query:
        await event.reply("Please provide a search query.")
        return
    
    index = 0
    manga_results_list = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.jikan.moe/v4/manga?q={query}&order_by=favorites&sort=desc&sfw=true") as response:
                if response.status == 200:
                    results = await response.json()
                else:
                    await event.reply(f"API Error: Status {response.status}")
                    return
        
        for result in results.get('data', []):
            # Skip unwanted tags
            if any(tag.get("name") in ["Hentai", "Ecchi", "Erotica"] for tag in result.get("genres", [])):
                continue
            
            # Safely access nested properties
            image_url = result.get("images", {}).get("jpg", {}).get("large_image_url", "")
            year = result.get("published", {}).get("prop", {}).get("from", {}).get("year")
            
            this_result = {
                "url": result.get("url", ""),
                "image_url": image_url,
                "title": result.get("title", "Unknown"),
                "chapters": result.get("chapters", "Unknown"),
                "the_type": result.get("type", "Unknown"),
                "year": year,
                "score": result.get("score", "N/A"),
                "themes": ", ".join([theme.get("name", "") for theme in result.get("themes", [])]) or "Unknown",
                "genres": ", ".join([genre.get("name", "") for genre in result.get("genres", [])]) or "Unknown",
            }
            manga_results_list.append(this_result)
            index += 1
            if index == 10:
                break
    except Exception as e:
        await event.reply(f"Error fetching data: {str(e)}")
        return

    if index == 0:
        await event.reply("No results found.")
        return

    try:
        buttons = [
            [Button.inline("Previous", data="mangaprev"), Button.inline("Next", data="manganext")],
            [Button.url("Open in MAL", manga_results_list[0]['url'])]
        ]
        
        caption = (
            f"__**{1}/{len(manga_results_list)}**__\n"
            f"**🎗️ Title:** {manga_results_list[0]['title']}\n"
            f"**👓 Type:** {manga_results_list[0]['the_type']}\n"
            f"**⭐ Score:** {manga_results_list[0]['score']}\n"
            f"**📃 Chapters:** {manga_results_list[0]['chapters']}\n"
            f"**📅 Year:** {manga_results_list[0]['year']}\n"
            f"**🎆 Themes:** {manga_results_list[0]['themes']}\n"
            f"**🎞️ Genres:** {manga_results_list[0]['genres']}"
        )
        sent_msg = await event.client.send_file(
            chat.id,
            manga_results_list[0]['image_url'],
            caption=caption,
            buttons=buttons
        )
        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "CREATE TABLE IF NOT EXISTS manga (message_id TEXT, current_index INTEGER, manga_result_list TEXT)"
                )
                await cursor.execute(
                    "INSERT INTO manga (message_id, current_index, manga_result_list) VALUES (?, ?, ?)",
                    (str(sent_msg.id), 0, str(manga_results_list))
                )
                await connection.commit()
    except Exception as e:
        await event.reply(f"Error displaying results: {str(e)}")

# ---------------------------
# Anime Command Handler
# ---------------------------
async def anime_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "anime")
    
    text = event.message.message
    query = text.replace("/anime", "").replace(f"@{BOT_USERNAME}", "").strip()
    if not query:
        await event.reply("Please provide a search query.")
        return

    index = 0
    anime_results_list = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.jikan.moe/v4/anime?q={query}&order_by=favorites&sort=desc&sfw=true") as response:
                if response.status == 200:
                    results = await response.json()
                else:
                    await event.reply(f"API Error: Status {response.status}")
                    return

        for result in results.get('data', []):
            # Skip unwanted genres
            if any(tag.get("name") in ["Hentai", "Ecchi", "Erotica"] for tag in result.get("genres", [])):
                continue
                
            # Safely access nested properties
            image_url = result.get("images", {}).get("jpg", {}).get("large_image_url", "")
            trailer_url = result.get("trailer", {}).get("url")
            year = result.get("aired", {}).get("prop", {}).get("from", {}).get("year")
            
            this_result = {
                "url": result.get("url", ""),
                "image_url": image_url,
                "trailer": trailer_url,
                "title": result.get("title", "Unknown"),
                "source": result.get("source", "Unknown"),
                "episodes": result.get("episodes", "Unknown"),
                "the_type": result.get("type", "Unknown"),
                "year": year,
                "score": result.get("score", "N/A"),
                "themes": ", ".join([theme.get("name", "") for theme in result.get("themes", [])]) or "Unknown",
                "studios": ", ".join([studio.get("name", "") for studio in result.get("studios", [])]) or "Unknown",
                "genres": ", ".join([genre.get("name", "") for genre in result.get("genres", [])]) or "Unknown",
            }
            anime_results_list.append(this_result)
            index += 1
            if index == 10:
                break
    except Exception as e:
        await event.reply(f"Error fetching data: {str(e)}")
        return

    if index == 0:
        await event.reply("No results found.")
        return

    try:
        if anime_results_list[0]['trailer'] is None:
            buttons = [
                [Button.inline("Previous", data="animeprev"), Button.inline("Next", data="animenext")],
                [Button.url("Open in MAL", anime_results_list[0]['url'])]
            ]
        else:
            buttons = [
                [Button.inline("Previous", data="animeprev"), Button.inline("Next", data="animenext")],
                [Button.url("Open in MAL", anime_results_list[0]['url'])],
                [Button.url("Watch Trailer", anime_results_list[0]['trailer'])]
            ]
        caption = (
            f"__**{1}/{len(anime_results_list)}**__\n"
            f"**🎗️ Title:** {anime_results_list[0]['title']}\n"
            f"**👓 Type:** {anime_results_list[0]['the_type']}\n"
            f"**⭐ Score:** {anime_results_list[0]['score']}\n"
            f"**📃 Episodes:** {anime_results_list[0]['episodes']}\n"
            f"**📅 Year:** {anime_results_list[0]['year']}\n"
            f"**🎆 Themes:** {anime_results_list[0]['themes']}\n"
            f"**🎞️ Genres:** {anime_results_list[0]['genres']}\n"
            f"**🏢 Studio:** {anime_results_list[0]['studios']}\n"
            f"**🧬 Source:** {anime_results_list[0]['source']}"
        )
        sent_msg = await event.client.send_file(
            chat.id,
            anime_results_list[0]['image_url'],
            caption=caption,
            buttons=buttons
        )
        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "CREATE TABLE IF NOT EXISTS anime (message_id TEXT, current_index INTEGER, anime_result_list TEXT)"
                )
                await cursor.execute(
                    "INSERT INTO anime (message_id, current_index, anime_result_list) VALUES (?, ?, ?)",
                    (str(sent_msg.id), 0, str(anime_results_list))
                )
                await connection.commit()
    except Exception as e:
        await event.reply(f"Error displaying results: {str(e)}")

# ---------------------------
# AGHPB Command Handler
# ---------------------------
async def aghpb_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "aghpb")
    
    url = "https://api.devgoldy.xyz/aghpb/v1/random"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_bytes = await response.read()
                    image_file = io.BytesIO(image_bytes)
                    image_file.name = "aghpb.jpg"  # Add a filename
                    await event.reply(file=image_file)
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching image: {str(e)}")

# ---------------------------
# Echo Command Handler
# ---------------------------
async def echo_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "echo")
    
    parts = event.message.message.split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip() == "":
        await event.reply("Type something in the message")
    else:
        await event.reply(parts[1].strip())

# ---------------------------
# Ping Command Handler
# ---------------------------
async def ping_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "ping")
    
    try:
        initial_latency = measure_latency(host='telegram.org')
        if not initial_latency or len(initial_latency) == 0:
            initial_latency_ms = "Failed to measure"
        else:
            initial_latency_ms = f"{int(initial_latency[0])}ms"
            
        start_time = time.time()
        sent_message = await event.reply("...")
        end_time = time.time()
        round_latency = int((end_time - start_time) * 1000)
        await sent_message.edit(
            text=f"Pong!\nInitial response: `{initial_latency_ms}`\nRound-trip: `{round_latency}ms`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await event.reply(f"Error measuring latency: {str(e)}")

# ---------------------------
# Timer Command Handler
# ---------------------------
async def timer_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "timer")
    
    text = event.message.message
    stripped = text.replace("/timer", "").replace(f"@{BOT_USERNAME}", "").strip()
    if " " in stripped:
        parts = stripped.split(" ", 1)
        time_str = parts[0]
        reason = parts[1]
    else:
        time_str = stripped
        reason = ""
    
    if not time_str:
        await event.reply(
            "Type time and time unit (s, m, h, d, w, mo, y) correctly\nFor example: `/timer 30m remind me of studying`",
            parse_mode="Markdown"
        )
        return

    time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "mo": 2592000, "y": 31104000}
    
    if len(time_str) < 2 or not time_str[:-1].isdigit():
        await event.reply(
            "Type time and time unit (s, m, h, d, w, mo, y) correctly\nFor example: `/timer 30m remind me of studying`",
            parse_mode="Markdown"
        )
        return
    
    time_unit = time_str[-1]
    if time_str[-2:] == "mo" and len(time_str) >= 3:
        time_unit = "mo"
        input_number = time_str[:-2]
    else:
        input_number = time_str[:-1]
    
    time_unit_number = time_units.get(time_unit)
    if time_unit_number is None:
        await event.reply(
            "Invalid time unit. Use s (seconds), m (minutes), h (hours), d (days), w (weeks), mo (months), or y (years)",
            parse_mode="Markdown"
        )
        return
    
    try:
        sleep_duration = int(time_unit_number) * int(input_number)
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=sleep_duration)
        
        time_unit_words = {
            "s": "seconds", "m": "minutes", "h": "hours", 
            "d": "days", "w": "weeks", "mo": "months", "y": "years"
        }
        time_unit_word = time_unit_words.get(time_unit, time_unit)
        
        if input_number == "1" and time_unit_word.endswith("s"):
            time_unit_word = time_unit_word[:-1]
        
        response_message = None
        if reason:
            response_message = await event.reply(
                f"Timer set to **{input_number} {time_unit_word}**\nReason: **{reason}**",
                parse_mode="Markdown"
            )
        else:
            response_message = await event.reply(
                f"Timer set to **{input_number} {time_unit_word}**",
                parse_mode="Markdown"
            )
        
        sender = await event.get_sender()
        user_id = sender.id
        message_id = event.id  # Get the ID of the command message
        
        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "CREATE TABLE IF NOT EXISTS timers (chat_id INTEGER, user_id INTEGER, end_time TEXT, reason TEXT, state TEXT, message_id INTEGER)"
                )
                await cursor.execute(
                    "INSERT INTO timers (chat_id, user_id, end_time, reason, state, message_id) VALUES (?, ?, ?, ?, 'active', ?)",
                    (chat.id, user_id, end_time.isoformat(), reason, message_id)
                )
                await connection.commit()
        delay = (end_time - datetime.datetime.now()).total_seconds()
        asyncio.create_task(schedule_timer(event.client, chat.id, delay, reason, message_id))
    except ValueError:
        await event.reply(
            "Please enter a valid number for the timer.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await event.reply(
            f"An error occurred: {str(e)}",
            parse_mode="Markdown"
        )

async def list_timers_command(event):
    """
    Lists all active timers for the current chat with time left until they expire.
    """
    chat = await event.get_chat()
    await save_usage(chat, "timers")
    now = datetime.datetime.now()
    
    async with aiosqlite.connect("db/database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "SELECT end_time, reason, user_id, state FROM timers WHERE chat_id = ? ORDER BY end_time",
                (chat.id,)
            )
            timers = await cursor.fetchall()
    
    if not timers:
        await event.reply("No active timers in this chat.")
        return
    
    lines = ["**📋 Active Timers:**\n"]
    active_timers = 0
    
    for i, (end_time_str, reason, user_id, state) in enumerate(timers, start=1):
        end_time = datetime.datetime.fromisoformat(end_time_str)
        diff = end_time - now
        
        if diff.total_seconds() > 0 and state == 'active':
            active_timers += 1
            
            # Try to get user info for a more friendly display
            # But avoid using @ which would ping users
            try:
                user = await event.client.get_entity(user_id)
                if user.username:
                    # Use the username without @ symbol to prevent pinging
                    user_display = f"{user.username}"
                else:
                    user_display = f"{user.first_name}"
            except:
                user_display = f"User {user_id}"
            
            # Format time remaining in a readable way
            d = diff.days
            h, remainder = divmod(diff.seconds, 3600)
            m, s = divmod(remainder, 60)
            
            time_parts = []
            if d > 0:
                time_parts.append(f"{d}d")
            if h > 0 or d > 0:
                time_parts.append(f"{h}h")
            if m > 0 or h > 0 or d > 0:
                time_parts.append(f"{m}m")
            time_parts.append(f"{s}s")
            
            time_left = " ".join(time_parts)
            end_time_formatted = end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            lines.append(
                f"**{active_timers}.** ⏰ **{time_left}** remaining\n"
                f"    📅 Ends: {end_time_formatted}\n"
                f"    👤 Set by: {user_display}\n"
                f"    📝 Reason: {reason or 'No reason provided'}\n"
            )
    
    if active_timers == 0:
        await event.reply("No active timers in this chat.")
        return
    
    # Handle message length limit (Telegram's max is 4096)
    full_message = "\n".join(lines)
    if len(full_message) <= 4000:  # Using 4000 to leave some buffer
        await event.reply(full_message)
    else:
        # Split message into multiple parts
        messages = []
        current_message = lines[0]  # Start with the header
        
        for i in range(1, len(lines)):
            # If adding this line would exceed limit, start a new message
            if len(current_message) + len(lines[i]) + 2 > 4000:
                messages.append(current_message)
                current_message = f"**📋 Active Timers (continued):**\n{lines[i]}"
            else:
                current_message += "\n\n" + lines[i]
        
        # Add the final message if it has content
        if current_message:
            messages.append(current_message)
        
        # Send all parts with a small delay between them
        for msg in messages:
            await event.reply(msg)
            await asyncio.sleep(0.5)  # Small delay to preserve message order

# ---------------------------
# Reverse Command Handler
# ---------------------------
async def reverse_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "reverse")
    parts = event.message.message.split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip() == "":
        await event.reply("Type some words.")
        return
    your_words = parts[1].strip()
    t_rev = your_words[::-1].replace("@", "@\u200B").replace("&", "&\u200B")
    await event.reply(f"🔁 {t_rev}")

# ---------------------------
# Slot Command Handler
# ---------------------------
async def slot_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "slot")
    emojis = "🍎🍊🍐🍋🍉🍇🍓🍒"
    a, b, c = [random.choice(emojis) for _ in range(3)]
    
    try:
        sender = await event.get_sender()
        sender_name = sender.first_name if hasattr(sender, 'first_name') else "User"
        slotmachine = f"**[ {a} {b} {c} ]\n{sender_name}**,"
        
        if a == b == c:
            await event.reply(f"{slotmachine} All matching, you won! 🎉")
        elif (a == b) or (a == c) or (b == c):
            await event.reply(f"{slotmachine} 2 in a row, you won! 🎉")
        else:
            await event.reply(f"{slotmachine} No match, you lost 😢")
    except Exception as e:
        await event.reply(f"Error in slot game: {str(e)}")

# ---------------------------
# Coinflip Command Handler
# ---------------------------
async def coinflip_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "coinflip")
    
    result = random.choice(["Heads", "Tails"])
    try:
        sender = await event.get_sender()
        sender_name = sender.first_name if hasattr(sender, 'first_name') else "User"
        await event.reply(f"**{sender_name}** flipped a coin and got **{result}**!")
    except Exception as e:
        await event.reply(f"Coin flip result: **{result}**")

# ---------------------------
# Meme Command Handler (using PRAW)
# ---------------------------
async def meme_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "meme")
    
    try:
        # Initialize Reddit API
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            check_for_async=False
        )
        
        # Choose a meme subreddit
        subreddit = reddit.subreddit("Animemes")
        
        # Get hot submissions
        all_subs = []
        for submission in subreddit.hot(limit=50):
            # Filter out non-image posts and stickied posts
            if (submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif')) and 
                not submission.stickied and not submission.is_self):
                all_subs.append(submission)
        
        if not all_subs:
            await event.reply("No suitable memes found. Try again later.")
            return
            
        # Select a random submission
        random_sub = random.choice(all_subs)
        name = random_sub.title
        url = random_sub.url
        
        # Send the meme
        await event.client.send_file(chat.id, url, caption=name)
    except Exception as e:
        await event.reply(f"Error fetching meme: {str(e)}")

# ---------------------------
# Geekjoke Command Handler
# ---------------------------
async def geekjoke_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "geekjoke")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://geek-jokes.sameerkumar.website/api?format=json") as response:
                if response.status == 200:
                    data = await response.json()
                    joke = data.get('joke', '')
                    if joke:
                        await event.reply(joke)
                    else:
                        await event.reply("Couldn't fetch a joke. Try again later.")
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching joke: {str(e)}")

# ---------------------------
# Dadjoke Command Handler
# ---------------------------
async def dadjoke_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "dadjoke")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://icanhazdadjoke.com/slack") as response:
                if response.status == 200:
                    data = await response.json()
                    if 'attachments' in data and data['attachments']:
                        joke = data['attachments'][0]['text']
                        await event.reply(joke)
                    else:
                        await event.reply("Couldn't fetch a joke. Try again later.")
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching joke: {str(e)}")

# ---------------------------
# Dog Command Handler
# ---------------------------
async def dog_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "dog")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://random.dog/woof.json") as response:
                if response.status == 200:
                    data = await response.json()
                    dog_url = data.get('url', '')
                    
                    if not dog_url:
                        await event.reply("Couldn't fetch a dog image. Try again later.")
                        return
                        
                    if dog_url.endswith((".mp4", ".webm")):
                        await event.client.send_file(chat.id, dog_url, supports_streaming=True)
                    elif dog_url.endswith((".jpg", ".jpeg", ".png")):
                        await event.client.send_file(chat.id, dog_url)
                    elif dog_url.endswith(".gif"):
                        await event.client.send_file(chat.id, dog_url)
                    else:
                        await event.reply(f"Unsupported file type: {dog_url}")
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching dog image: {str(e)}")

# ---------------------------
# Affirmation Command Handler
# ---------------------------
async def affirmation_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "affirmation")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.affirmations.dev/") as response:
                if response.status == 200:
                    data = await response.json()
                    affirmation_text = data.get('affirmation', '')
                    if affirmation_text:
                        await event.reply(affirmation_text)
                    else:
                        await event.reply("Couldn't fetch an affirmation. Try again later.")
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching affirmation: {str(e)}")


# ---------------------------
# Advice Command Handler
# ---------------------------
async def advice_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "advice")
    headers = {"Accept": "application/json"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get("https://api.adviceslip.com/advice") as response:
            data = await response.json(content_type="text/html")
    advice_text = data['slip']['advice']
    await event.reply(advice_text)

# ---------------------------
# Gemini Command Handler
# ---------------------------
async def gemini_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "gemini")
    try:
        prompt = event.message.message.replace("/gemini", "").replace(f"@{BOT_USERNAME}", "").strip()
        if prompt == "":
            await event.reply("Please write your prompt on the same message.")
            return
        api_key = GEMINI_API_KEY
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        response_text = response.text
        limit = 4000
        if len(response_text) > limit:
            parts = [response_text[i: i + limit] for i in range(0, len(response_text), limit)]
            for part in parts:
                await event.reply(f"Gemini Pro: {part}")
                await asyncio.sleep(0.5)
        else:
            await event.reply(f"Gemini Pro: {response_text}")
    except Exception as e:
        print(f"Gemini error: {e}")
        await event.reply("Sorry, an unexpected error had occured.")

# ---------------------------
# Imagine Command Handler
# ---------------------------
async def imagine_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "imagine")
    try:
        something_to_imagine = event.message.message.replace("/imagine", "").replace(f"@{BOT_USERNAME}", "").strip()
        if not something_to_imagine:
            await event.reply("You have to describe the image.")
            return

        waiting_msg = await event.reply("Wait a moment...")
        API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
        API_TOKEN = HUGGINGFACE_TOKEN
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        payload = {"inputs": f"{something_to_imagine}, mdjrny-v4 style"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(API_URL, json=payload) as response:
                image_bytes = await response.read()
        file = io.BytesIO(image_bytes)
        file.name = "image.png"
        await event.client.send_file(chat.id, file)
        await waiting_msg.delete()
    except Exception:
        await event.reply("Sorry, I ran into an error.")