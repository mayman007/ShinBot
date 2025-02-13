import asyncio
import datetime
import io
import os
import aiohttp
import aiosqlite
import ast
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import random
from dotenv import dotenv_values
import time
import praw
from tcp_latency import measure_latency
import google.generativeai as genai
import yt_dlp

# Load variables from the .env file
config = dotenv_values(".env")

# Save Commands Usage in Database
async def save_usage(chat_object, command_name: str):
    if chat_object.type in ['group', 'supergroup']:
        chat_id = str(chat_object.id)
        chat_name = str(chat_object.title)
        chat_type = str(chat_object.type)
        # chat_members = str(chat_object.get_member_count())
        # chat_invite = str(chat_object.invite_link if chat_object.invite_link else "_")
        chat_members = "idk"
        chat_invite = "idk"
    elif chat_object.type in ['private', 'bot']:
        chat_id = str(chat_object.id)
        chat_name = str(chat_object.username if chat_object.username else chat_object.first_name)
        chat_type = str(chat_object.type)
        chat_members = str("_")
        chat_invite = str("_")
        
    async with aiosqlite.connect("usage.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(f"CREATE TABLE IF NOT EXISTS {command_name} (id TEXT, name TEXT, usage INTEGER, type TEXT, members TEXT, invite TEXT)")
            cursor = await cursor.execute(f"SELECT * FROM {command_name} WHERE id = ?", (chat_id,))
            row = await cursor.fetchone()
            if row == None:
                await cursor.execute(f"INSERT INTO {command_name} (id, name, usage, type, members, invite) VALUES (?, ?, ?, ?, ?, ?)", (chat_id, chat_name, 1, chat_type, chat_members, chat_invite,))
            else:
                await cursor.execute(f"UPDATE {command_name} SET usage = ? WHERE id = ?", (row[2] + 1, chat_id))
            await connection.commit()

async def usagedata_command(update: Update, context):
    if update.message.from_user.id == 1201645998:
        async with aiosqlite.connect("usage.db") as connection:
            async with connection.cursor() as cursor:
                data = await cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = await data.fetchall()
                data_message = "Here is all the usage data!\n"
                for table in tables:
                    table_name = table[0]
                    data_message += "===================\n\n"
                    data_message += f"**{table_name}**\n"
                    data = await cursor.execute(f"SELECT * FROM {table_name};")
                    rows = await data.fetchall()
                    for row in rows:
                        data_message += f"- Chat ID: {row[0]}\n- Chat Name: **{row[1]}**\n- Usage Count: **{row[2]}**\n- Chat Type: {row[3]}\n- Chat Members: {row[4]}\n- Chat Invite: {row[5]}\n\n"
        
        limit = 3800
        if len(data_message) > limit:
            result = [data_message[i: i + limit] for i in range(0, len(data_message), limit)]
            for half in result:
                await update.message.reply_text(half)
                await asyncio.sleep(0.5)
        else:
            await update.message.reply_text(data_message)
    else:
        await update.message.reply_text("You're not allowed to use this command")

async def start_command(update: Update, context):
    await update.message.reply_text(
        f"Hello {update.message.from_user.first_name}, My name is Shin and I'm developed by @Mayman007tg.\n"
        "I'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me."
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
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
        "/imagine - Generate AI images\n"
        "/manga - Search Manga\n"
        "/meme - Get a random meme from Reddit\n"
        "/ping - Get bot's latency\n"
        "/reverse - Reverse your words\n"
        "/slot - A slot game\n"
        "/timer - Set yourself a timer\n",
    )

# Handler for character search
async def character_command(update: Update, context):
    chat = await context.bot.get_chat(update.message.chat_id)
    await save_usage(chat, "character")
    
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Please provide a search query.")
        return

    index = 0
    character_results_list = []
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.jikan.moe/v4/characters?q={query}&order_by=favorites&sort=desc") as response:
            results = await response.json()
    
    for result in results['data']:
        this_result_dict = {
            'url': result["url"],
            'image_url': result["images"]["jpg"]["image_url"],
            'name': result["name"],
            'favorites': result["favorites"],
            'about': "" if result["about"] is None else (result["about"][:800] + "..." if len(result["about"]) > 800 else result["about"])
        }
        character_results_list.append(this_result_dict)
        index += 1
        if index == 10:
            break

    if index == 0:
        await update.message.reply_text("No results found.")
        return

    keyboard = [[InlineKeyboardButton("Open in MAL", url=character_results_list[0]['url'])]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = await update.message.reply_photo(
        photo=character_results_list[0]['image_url'],
        caption=f"**🎗️ Name:** {character_results_list[0]['name']}\n"
                f"**⭐ Favorites:** {character_results_list[0]['favorites']}\n"
                f"**👓 About:** {character_results_list[0]['about']}",
        reply_markup=reply_markup
    )

    async with aiosqlite.connect("database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "CREATE TABLE IF NOT EXISTS character (message_id TEXT, current_index INTEGER, character_result_list TEXT)"
            )
            await cursor.execute(
                "INSERT INTO character (message_id, current_index, character_result_list) VALUES (?, ?, ?)",
                (msg.message_id, 0, str(character_results_list))
            )
            await connection.commit()

# ---------- Manga Command Handler ----------
async def manga_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "manga")

    text = update.message.text
    query = text.replace("/manga", "").replace("@shinobi7kbot", "").strip()
    if not query:
        await update.message.reply_text("Please provide a search query.")
        return

    index = 0
    manga_results_list = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.jikan.moe/v4/manga?q={query}&order_by=favorites&sort=desc&sfw=true") as response:
            results = await response.json()

    for result in results.get('data', []):
        # Skip if genres contain unwanted tags
        if any(tag in str(result.get("genres", [])) for tag in ("Hentai", "Ecchi", "Erotica")):
            continue

        this_result = {
            "url": result.get("url"),
            "image_url": result.get("images", {}).get("jpg", {}).get("large_image_url"),
            "title": result.get("title"),
            "chapters": result.get("chapters"),
            "the_type": result.get("type"),
            "year": result.get("published", {}).get("prop", {}).get("from", {}).get("year"),
            "score": result.get("score"),
            "themes": ", ".join([theme.get("name") for theme in result.get("themes", [])]),
            "genres": ", ".join([genre.get("name") for genre in result.get("genres", [])]),
        }
        manga_results_list.append(this_result)
        index += 1
        if index == 10:
            break

    if index == 0:
        await update.message.reply_text("No results found.")
        return

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Previous", callback_data="mangaprev"),
            InlineKeyboardButton("Next", callback_data="manganext")
        ],
        [
            InlineKeyboardButton("Open in MAL", url=manga_results_list[0]['url'])
        ]
    ])

    caption = (
        f"__**{1}**__\n"
        f"**🎗️ Title:** {manga_results_list[0]['title']}\n"
        f"**👓 Type:** {manga_results_list[0]['the_type']}\n"
        f"**⭐ Score:** {manga_results_list[0]['score']}\n"
        f"**📃 Chapters:** {manga_results_list[0]['chapters']}\n"
        f"**📅 Year:** {manga_results_list[0]['year']}\n"
        f"**🎆 Themes:** {manga_results_list[0]['themes']}\n"
        f"**🎞️ Genres:** {manga_results_list[0]['genres']}"
    )

    sent_msg = await update.message.reply_photo(
        photo=manga_results_list[0]['image_url'],
        caption=caption,
        reply_markup=buttons,
    )

    # Save the manga result to the database
    async with aiosqlite.connect("database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "CREATE TABLE IF NOT EXISTS manga (message_id TEXT, current_index INTEGER, manga_result_list TEXT)"
            )
            await cursor.execute(
                "INSERT INTO manga (message_id, current_index, manga_result_list) VALUES (?, ?, ?)",
                (str(sent_msg.message_id), 0, str(manga_results_list))
            )
            await connection.commit()

# ---------- Anime Command Handler ----------
async def anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "anime")

    text = update.message.text
    query = text.replace("/anime", "").replace("@shinobi7kbot", "").strip()
    if not query:
        await update.message.reply_text("Please provide a search query.")
        return

    index = 0
    anime_results_list = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.jikan.moe/v4/anime?q={query}&order_by=favorites&sort=desc&sfw=true") as response:
            results = await response.json()

    for result in results.get('data', []):
        if any(tag in str(result.get("genres", [])) for tag in ("Hentai", "Ecchi", "Erotica")):
            continue

        this_result = {
            "url": result.get("url"),
            "image_url": result.get("images", {}).get("jpg", {}).get("large_image_url"),
            "trailer": result.get("trailer", {}).get("url"),
            "title": result.get("title"),
            "source": result.get("source"),
            "episodes": result.get("episodes"),
            "the_type": result.get("type"),
            "year": result.get("aired", {}).get("prop", {}).get("from", {}).get("year"),
            "score": result.get("score"),
            "themes": ", ".join([theme.get("name") for theme in result.get("themes", [])]),
            "studios": ", ".join([studio.get("name") for studio in result.get("studios", [])]),
            "genres": ", ".join([genre.get("name") for genre in result.get("genres", [])]),
        }
        anime_results_list.append(this_result)
        index += 1
        if index == 10:
            break

    if index == 0:
        await update.message.reply_text("No results found.")
        return

    # Build buttons depending on whether a trailer exists
    if anime_results_list[0]['trailer'] is None:
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Previous", callback_data="animeprev"),
                InlineKeyboardButton("Next", callback_data="animenext")
            ],
            [
                InlineKeyboardButton("Open in MAL", url=anime_results_list[0]['url'])
            ]
        ])
    else:
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Previous", callback_data="animeprev"),
                InlineKeyboardButton("Next", callback_data="animenext")
            ],
            [
                InlineKeyboardButton("Open in MAL", url=anime_results_list[0]['url'])
            ],
            [
                InlineKeyboardButton("Watch Trailer", url=anime_results_list[0]['trailer'])
            ]
        ])

    caption = (
        f"__**{1}**__\n"
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

    sent_msg = await update.message.reply_photo(
        photo=anime_results_list[0]['image_url'],
        caption=caption,
        reply_markup=buttons,
    )

    async with aiosqlite.connect("database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "CREATE TABLE IF NOT EXISTS anime (message_id TEXT, current_index INTEGER, anime_result_list TEXT)"
            )
            await cursor.execute(
                "INSERT INTO anime (message_id, current_index, anime_result_list) VALUES (?, ?, ?)",
                (str(sent_msg.message_id), 0, str(anime_results_list))
            )
            await connection.commit()

# ---------- Callback Query Handler for Pagination ----------
async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("anime"):
        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM anime WHERE message_id = ?", (str(query.message.message_id),)
                )
                db_data = await cursor.fetchall()

        if not db_data:
            await query.answer("No data found.")
            return

        current_index = db_data[0][1]
        anime_results_list = ast.literal_eval(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
        btn_type = "prev" if "prev" in data else "next" if "next" in data else None
        if current_index == 0:
            prev_index = 0
            next_index = 1
        elif current_index == 4:
            prev_index = 3
            next_index = 4
        else:
            prev_index = current_index - 1
            next_index = current_index + 1

        updated_index = prev_index if btn_type == "prev" else next_index if btn_type == "next" else current_index
        if updated_index == current_index:
            await query.answer()
            return

        image_link = anime_results_list[updated_index]['image_url']
        message_content = (
            f"__**{updated_index + 1}**__\n"
            f"**🎗️ Title:** {anime_results_list[updated_index]['title']}\n"
            f"**👓 Type:** {anime_results_list[updated_index]['the_type']}\n"
            f"**⭐ Score:** {anime_results_list[updated_index]['score']}\n"
            f"**📃 Episodes:** {anime_results_list[updated_index]['episodes']}\n"
            f"**📅 Year:** {anime_results_list[updated_index]['year']}\n"
            f"**🎆 Themes:** {anime_results_list[updated_index]['themes']}\n"
            f"**🎞️ Genres:** {anime_results_list[updated_index]['genres']}\n"
            f"**🏢 Studio:** {anime_results_list[updated_index]['studios']}\n"
            f"**🧬 Source:** {anime_results_list[updated_index]['source']}"
        )

        if anime_results_list[updated_index]['trailer'] in (None, "None"):
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Previous", callback_data="animeprev"),
                    InlineKeyboardButton("Next", callback_data="animenext")
                ],
                [
                    InlineKeyboardButton("Open in MAL", url=anime_results_list[updated_index]['url'])
                ]
            ])
        else:
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Previous", callback_data="animeprev"),
                    InlineKeyboardButton("Next", callback_data="animenext")
                ],
                [
                    InlineKeyboardButton("Open in MAL", url=anime_results_list[updated_index]['url'])
                ],
                [
                    InlineKeyboardButton("Watch Trailer", url=anime_results_list[updated_index]['trailer'])
                ]
            ])

        await query.message.edit_media(
            media=InputMediaPhoto(media=image_link, caption=message_content)
        )
        await query.message.edit_reply_markup(reply_markup=buttons)
        await query.answer()

        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "UPDATE anime SET current_index = ? WHERE message_id = ?",
                    (updated_index, str(query.message.message_id))
                )
                await connection.commit()

    elif data.startswith("manga"):
        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM manga WHERE message_id = ?", (str(query.message.message_id),)
                )
                db_data = await cursor.fetchall()

        if not db_data:
            await query.answer("No data found.")
            return

        current_index = db_data[0][1]
        manga_results_list = ast.literal_eval(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
        btn_type = "prev" if "prev" in data else "next" if "next" in data else None
        if current_index == 0:
            prev_index = 0
            next_index = 1
        elif current_index == 4:
            prev_index = 3
            next_index = 4
        else:
            prev_index = current_index - 1
            next_index = current_index + 1

        updated_index = prev_index if btn_type == "prev" else next_index if btn_type == "next" else current_index
        if updated_index == current_index:
            await query.answer()
            return

        image_link = manga_results_list[updated_index]['image_url']
        message_content = (
            f"__**{updated_index + 1}**__\n"
            f"**🎗️ Title:** {manga_results_list[updated_index]['title']}\n"
            f"**👓 Type:** {manga_results_list[updated_index]['the_type']}\n"
            f"**⭐ Score:** {manga_results_list[updated_index]['score']}\n"
            f"**📃 Chapters:** {manga_results_list[updated_index]['chapters']}\n"
            f"**📅 Year:** {manga_results_list[updated_index]['year']}\n"
            f"**🎆 Themes:** {manga_results_list[updated_index]['themes']}\n"
            f"**🎞️ Genres:** {manga_results_list[updated_index]['genres']}"
        )
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Previous", callback_data="mangaprev"),
                InlineKeyboardButton("Next", callback_data="manganext")
            ],
            [
                InlineKeyboardButton("Open in MAL", url=manga_results_list[updated_index]['url'])
            ]
        ])

        await query.message.edit_media(
            media=InputMediaPhoto(media=image_link, caption=message_content)
        )
        await query.message.edit_reply_markup(reply_markup=buttons)
        await query.answer()

        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "UPDATE manga SET current_index = ? WHERE message_id = ?",
                    (updated_index, str(query.message.message_id))
                )
                await connection.commit()

# ---------------------------
# AGHPB Command Handler
# ---------------------------
async def aghpb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "aghpb")

    url = "https://api.devgoldy.xyz/aghpb/v1/random"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            image_bytes = await response.read()
    # Create a file-like object from the image bytes
    image_file = io.BytesIO(image_bytes)
    await update.message.reply_photo(photo=image_file)


# ---------------------------
# Echo Command Handler
# ---------------------------
async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "echo")

    # Remove the command text and bot username from the message text
    text = update.message.text.replace("/echo", "").replace("@shinobi7kbot", "").strip()
    if text == "": await update.message.reply_text("Type something in the message")
    else: await update.message.reply_text(text)


# ---------------------------
# Ping Command Handler
# ---------------------------
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "ping")

    initial_latency = int(measure_latency(host='telegram.org')[0])
    start_time = time.time()
    sent_message = await update.message.reply_text("...")
    end_time = time.time()
    round_latency = int((end_time - start_time) * 1000)
    # Use Markdown (or HTML) to format the text as desired
    await sent_message.edit_text(
        f"Pong!\nInitial response: `{initial_latency}ms`\nRound-trip: `{round_latency}ms`",
        parse_mode="Markdown"
    )


# ---------------------------
# Timer Command Handler
# ---------------------------
async def timer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "timer")

    # Remove command and bot username from the text
    message_text = update.message.text.replace("/timer", "").replace("@shinobi7kbot", "").strip()
    if " " in message_text:
        parts = message_text.split(" ", 1)
        time_str = parts[0]
        reason = parts[1]
    else:
        time_str = message_text
        reason = ""

    if not time_str:
        await update.message.reply_text(
            "Type time and time unit (s, m, h, d, w, y) correctly\nFor example: `/timer 30m remind me of studying`",
            parse_mode="Markdown"
        )
        return

    get_time = {
        "s": 1, "m": 60, "h": 3600, "d": 86400,
        "w": 604800, "mo": 2592000, "y": 31104000
    }
    time_unit = time_str[-1]
    time_unit_number = get_time.get(time_unit)
    input_number = time_str[:-1]
    try:
        int(input_number)
    except Exception:
        await update.message.reply_text(
            "Type time and time unit (s, m, h, d, w, y) correctly\nFor example: `/timer 30m remind me of studying`",
            parse_mode="Markdown"
        )
        return

    try:
        sleep_duration = int(time_unit_number) * int(input_number)
        # Convert the time unit into words
        if time_unit == "s":
            time_unit_word = "seconds"
        elif time_unit == "m":
            time_unit_word = "minutes"
        elif time_unit == "h":
            time_unit_word = "hours"
        elif time_unit == "d":
            time_unit_word = "days"
        elif time_unit == "w":
            time_unit_word = "weeks"
        elif time_unit == "mo":
            time_unit_word = "months"
        elif time_unit == "y":
            time_unit_word = "years"
        else:
            time_unit_word = time_unit

        # Make the unit singular if the number is 1
        if input_number == "1" and time_unit_word.endswith("s"):
            time_unit_word = time_unit_word[:-1]

        try:
            if reason:
                await update.message.reply_text(
                    f"Timer set to **{input_number} {time_unit_word}**\nReason: **{reason}**",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"Timer set to **{input_number} {time_unit_word}**",
                    parse_mode="Markdown"
                )
        except Exception:
            await update.message.reply_text(
                f"Timer set to **{input_number} {time_unit_word}**",
                parse_mode="Markdown"
            )
    except Exception:
        await update.message.reply_text(
            "Type time and time unit (s, m, h, d, w, y) correctly\nFor example: `/timer 30m remind me of studying`",
            parse_mode="Markdown"
        )
        return

    # message_id = update.message.id
    # chat_id = chat.id
    # start_timestamp = int(datetime.datetime.now().timestamp())
    
    # print(message_id)
    # print(chat_id)
    # print(start_timestamp)
    # print(datetime.timedelta(seconds=sleep_duration))

    # async with aiosqlite.connect("database.db") as connection:
    #     async with connection.cursor() as cursor:
    #         await cursor.execute(
    #             "CREATE TABLE IF NOT EXISTS timers (message_id ID, chat_id INTEGER, start_timestamp INTEGER, end_timestamp INTEGER, duration_in_seconds INTEGER, reason TEXT)"
    #         )
    #         await cursor.execute(
    #             "INSERT INTO character (message_id, chat_id, start_timestamp, end_timestamp, duration_in_seconds, reason) VALUES (?, ?, ?, ?, ?, ?)",
    #             (msg.message_id, 0, str(character_results_list))
    #         )
    #         await connection.commit()

    await asyncio.sleep(sleep_duration)
    try:
        if reason:
            await update.message.reply_text(
                f"Your timer that was set to **{input_number} {time_unit_word}** for **{reason}** has ended",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"Your timer that was set to **{input_number} {time_unit_word}** has ended",
                parse_mode="Markdown"
            )
    except Exception:
        await update.message.reply_text(
            f"Your timer that was set to **{input_number} {time_unit_word}** has ended",
            parse_mode="Markdown"
        )

# ---------------------------
# Reverse Command Handler
# ---------------------------
async def reverse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "reverse")

    your_words = update.message.text.replace("/reverse", "").replace("@shinobi7kbot", "").strip()
    if not your_words:
        await update.message.reply_text("Type some words.")
        return

    t_rev = your_words[::-1].replace("@", "@\u200B").replace("&", "&\u200B")
    await update.message.reply_text(f"🔁 {t_rev}")

# ---------------------------
# Slot Command Handler
# ---------------------------
async def slot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "slot")

    emojis = "🍎🍊🍐🍋🍉🍇🍓🍒"
    a, b, c = [random.choice(emojis) for _ in range(3)]
    # You can optionally set parse_mode="Markdown" if you want bold formatting.
    slotmachine = f"**[ {a} {b} {c} ]\n{update.message.from_user.first_name}**,"
    if a == b == c:
        await update.message.reply_text(f"{slotmachine} All matching, you won! 🎉")
    elif (a == b) or (a == c) or (b == c):
        await update.message.reply_text(f"{slotmachine} 2 in a row, you won! 🎉")
    else:
        await update.message.reply_text(f"{slotmachine} No match, you lost 😢")

# ---------------------------
# Coinflip Command Handler
# ---------------------------
async def coinflip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "coinflip")

    coinsides = ["Heads", "Tails"]
    result = random.choice(coinsides)
    await update.message.reply_text(
        f"**{update.message.from_user.first_name}** flipped a coin and got **{result}**!"
    )

# ---------------------------
# Meme Command Handler (using PRAW)
# ---------------------------
async def meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "meme")

    reddit = praw.Reddit(
        client_id=config.get("REDDIT_CLIENT_ID"),
        client_secret=config.get("REDDIT_CLIENT_SECRET"),
        user_agent="ShinobiBot",
        check_for_async=False
    )
    subreddit = reddit.subreddit("Animemes")
    all_subs = [submission for submission in subreddit.hot(limit=50)]
    random_sub = random.choice(all_subs)
    name = random_sub.title
    url = random_sub.url

    if ".gif" in url:
        await update.message.reply_animation(url, caption=name)
    elif ".mp4" in url:
        await update.message.reply_video(url, caption=name)
    else:
        await update.message.reply_photo(url, caption=name)

# ---------------------------
# Geekjoke Command Handler
# ---------------------------
async def geekjoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "geekjoke")

    async with aiohttp.ClientSession() as session:
        async with session.get("https://geek-jokes.sameerkumar.website/api?format=json") as response:
            data = await response.json()
    joke = data['joke']
    await update.message.reply_text(joke)

# ---------------------------
# Dadjoke Command Handler
# ---------------------------
async def dadjoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "dadjoke")

    async with aiohttp.ClientSession() as session:
        async with session.get("https://icanhazdadjoke.com/slack") as response:
            data = await response.json()
    joke = data['attachments'][0]['text']
    await update.message.reply_text(joke)

# ---------------------------
# Dog Command Handler
# ---------------------------
async def dog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "dog")

    async with aiohttp.ClientSession() as session:
        async with session.get("https://random.dog/woof.json") as response:
            data = await response.json()
    dog_url = data['url']
    if dog_url.endswith(".mp4"):
        await update.message.reply_video(dog_url)
    elif dog_url.endswith(".jpg") or dog_url.endswith(".png"):
        await update.message.reply_photo(dog_url)
    elif dog_url.endswith(".gif"):
        await update.message.reply_animation(dog_url)

# ---------------------------
# Affirmation Command Handler
# ---------------------------
async def affirmation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "affirmation")

    async with aiohttp.ClientSession() as session:
        async with session.get("https://www.affirmations.dev/") as response:
            data = await response.json()
    affirmation_text = data['affirmation']
    await update.message.reply_text(affirmation_text)

# ---------------------------
# Advice Command Handler
# ---------------------------
async def advice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "advice")

    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.adviceslip.com/advice", headers={"Accept": "application/json"}) as response:
            data = await response.json(content_type="text/html")
    advice_text = data['slip']['advice']
    await update.message.reply_text(advice_text)

# ---------------------------
# /gemini Command Handler
# ---------------------------
async def gemini_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "gemini")

    try:
        prompt = update.message.text.replace("/gemini", "").replace("@shinobi7kbot", "").strip()
        if prompt == "":
            await update.message.reply_text("Please write your prompt on the same message.")
            return

        api_key = config.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = await model.generate_content_async(prompt)
        response_text = response.text

        limit = 4000
        if len(response_text) > limit:
            parts = [response_text[i: i + limit] for i in range(0, len(response_text), limit)]
            for part in parts:
                await update.message.reply_text(f"Gemini Pro: {part}")
                await asyncio.sleep(0.5)
        else:
            await update.message.reply_text(f"Gemini Pro: {response_text}")
    except Exception as e:
        print(f"Gemini error: {e}")
        await update.message.reply_text("Sorry, an unexpected error had occured.")

async def imagine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await save_usage(chat, "imagine")

    # Remove command and bot username from the message text.
    something_to_imagine = update.message.text.replace("/imagine", "").replace("@shinobi7kbot", "").strip()
    if not something_to_imagine:
        await update.message.reply_text("You have to descripe the image.")
        return

    # Send a waiting message to the user
    waiting_msg = await update.message.reply_text("Wait a moment...")

    API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
    API_TOKEN = config.get("HUGGINGFACE_TOKEN")
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    payload = {"inputs": f"{something_to_imagine}, mdjrny-v4 style"}

    # Send the request to the Hugging Face Inference API
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(API_URL, json=payload) as response:
            image_bytes = await response.read()

    # Convert the received bytes to a file-like object and send it as a photo
    with io.BytesIO(image_bytes) as file:
        await update.message.reply_photo(photo=file)

    # Delete the waiting message
    await waiting_msg.delete()


# Store active downloads
active_downloads = {}

def get_video_info(url: str) -> dict:
    """Extract video information without downloading."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best'  # Default format if none selected
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            
            # Filter formats that have both video and audio
            for f in info['formats']:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    # Get file size
                    filesize = f.get('filesize', 0)
                    if filesize == 0:
                        filesize = f.get('filesize_approx', 0)
                    
                    # Skip files larger than 2GB (Telegram's limit)
                    if filesize > 2_000_000_000:
                        continue
                    
                    # Get resolution
                    resolution = f.get('resolution', 'unknown')
                    if resolution == 'unknown' and f.get('height'):
                        resolution = f'{f["height"]}p'
                    
                    # Calculate size in MB
                    size_mb = filesize / (1024 * 1024)
                    
                    formats.append({
                        'format_id': f['format_id'],
                        'ext': f.get('ext', 'mp4'),
                        'resolution': resolution,
                        'filesize': f'{size_mb:.1f}MB'
                    })
            
            return {
                'title': info['title'],
                'formats': formats,
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration')
            }
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

async def download_video(url: str, format_id: str) -> str:
    """Download video and return the file path."""
    # Create unique filename using timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_template = f'downloads/{timestamp}/%(title)s.%(ext)s'
    
    # Create downloads directory if it doesn't exist
    os.makedirs(f'downloads/{timestamp}', exist_ok=True)
    
    opts = {
        'format': format_id,
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Hi! Send me a YouTube link with /yt command to download videos.\n"
        "Example: /yt https://youtube.com/watch?v=..."
    )

async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /yt command."""
    # Get the URL from the command
    try:
        url = context.args[0]
    except IndexError:
        await update.message.reply_text("Please provide a YouTube URL.\nExample: /yt https://youtube.com/watch?v=...")
        return

    # Send a waiting message
    status_message = await update.message.reply_text("⏳ Getting video information...")

    try:
        # Get video information
        info = get_video_info(url)
        if not info:
            await status_message.edit_text("❌ Failed to get video information. Please try again.")
            return

        # Create inline keyboard with format options
        keyboard = []
        for fmt in info['formats']:
            text = f"{fmt['resolution']} ({fmt['filesize']})"
            callback_data = f"dl:{url}:{fmt['format_id']}"
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Update status message with format options
        await status_message.edit_text(
            f"📹 *{info['title']}*\n\nChoose video quality:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        await status_message.edit_text(f"❌ Error: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    # Parse callback data
    try:
        action, url, format_id = query.data.split(':', 2)
    except ValueError:
        await query.message.edit_text("❌ Invalid callback data")
        return

    if action != 'dl':
        return

    # Update message to show download status
    status_message = await query.message.edit_text("⏳ Downloading video...")

    try:
        # Download the video
        filepath = await download_video(url, format_id)
        if not filepath:
            await status_message.edit_text("❌ Download failed")
            return

        # Send the video file
        await status_message.edit_text("📤 Uploading to Telegram...")
        with open(filepath, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                caption="✅ Here's your video!"
            )
        
        # Clean up
        await status_message.edit_text("✅ Download completed!")
        os.remove(filepath)
        os.rmdir(os.path.dirname(filepath))

    except Exception as e:
        await status_message.edit_text(f"❌ Error: {str(e)}")
        # Clean up in case of error
        if 'filepath' in locals():
            try:
                os.remove(filepath)
                os.rmdir(os.path.dirname(filepath))
            except:
                pass


# Message events
async def message_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ensure the message and its text exist
    if update.message is None or update.message.text is None:
        return

    text = update.message.text

    # تثبيحات
    if text.startswith("ثبح ") or text == "ثبح":
        await update.message.reply_text("ثباحو")
    elif text.startswith("ثباحو ") or text == "ثباحو":
        await update.message.reply_text("ثبح")
    elif text.startswith("مثائو ") or text == "مثائو":
        await update.message.reply_text("مثا")
    elif text.startswith("مثا ") or text == "مثا":
        await update.message.reply_text("مثائو")

    # يالبوت
    if "يالبوت" in text:
        normal_responses = [
            "اكيد يسطا", "اكيد يبرو", "بدون شك", "يب اكيد", "طبعا", "اومال", "ايوه",
            "يب", "يب يب", "اتكل علي الله يعم", "مش فايقلك",
            "هي دي محتاجه سؤال!؟", "لا", "انا بقولك لا", "اكيد لا", "نوب", "معرفش",
            "اكيد يغالي", "اكيد ينقم", "لا هه", "صدقني انا ذات نفسي معرفش", "انا لو أعرف هقولك"
        ]
        hellos = ["نعم", "نعم يغالي", "نعم ينقم", "عايز ايه", "نعم يخويا"]
        steins_keys = ["stein", "شتاين", "ستاين"]
        steins = [
            "شتاينز الأعظم", "شتاينز فوق", "شتاينز فوق مستوي التقييم البشري", "شتاينز اعظم انمي"
        ]
        shinobi_keywords = ["shinobi", "شنوبي", "شنبي", "شنوب", "شينوبي"]
        father = [
            "شنوبي ابويا وعمي وعم عيالي", "شنبي ابويا وعمي", "شنوبي احسن اب في العالم"
        ]
        azab = [
            "ده حنين عليا خالث", "بابا شنبي مش بيمد ايده عليا", "مش بيلمسني"
        ]
        tabla = [
            "لا طبعا يغالي", "شنوبي عمي وعم عيالي", "شنوبي عمك", "شنوبي فوق"
        ]
        love = ["حبك", "حبق", "وانا كمان يغالي", "+1"]
        win = ["مش هتكسب هه", "نصيبك مش هتكسب", "انا بقولك لا", "على ضمانتي"]
        elhal = ["الحمدلله يخويا", "الحمدلله يغالي", "تمام الحمدلله"]

        # me responses
        if "انا" in text:
            if update.message.from_user and update.message.from_user.username == "Shinobi7k":
                if "ابوك" in text:
                    await update.message.reply_text(random.choice(father))
                    return

        # shinobi responses
        for word in shinobi_keywords:
            if word in text:
                if "ابوك" in text:
                    await update.message.reply_text(random.choice(father))
                    return
                if "بيعذبك" in text:
                    await update.message.reply_text(random.choice(azab))
                    return
                if "بتطبل" in text:
                    await update.message.reply_text(random.choice(tabla))
                    return

        # steins responses
        for word in steins_keys:
            if word in text:
                await update.message.reply_text(random.choice(steins))
                return

        # exceptions
        if "هكسب" in text:
            await update.message.reply_text(random.choice(win))
            return
        if "حبك" in text or "حبق" in text:
            await update.message.reply_text(random.choice(love))
            return
        if "عامل ايه" in text or "عامل إيه" in text or "كيف حالك" in text:
            await update.message.reply_text(random.choice(elhal))
            return

        # normal responses
        if " " in text:
            await update.message.reply_text(random.choice(normal_responses))
        else:
            await update.message.reply_text(random.choice(hellos))

def main():
    # Create downloads directory
    os.makedirs('downloads', exist_ok=True)
    # Initialize bot with token from config
    application = Application.builder().token(config.get("BOT_TOKEN")).concurrent_updates(True).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("usagedata", usagedata_command))
    application.add_handler(CommandHandler("character", character_command))
    application.add_handler(CommandHandler("anime", anime_command))
    application.add_handler(CommandHandler("manga", manga_command))
    application.add_handler(CommandHandler("aghpb", aghpb_command))
    application.add_handler(CommandHandler("echo", echo_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("timer", timer_command))
    application.add_handler(CommandHandler("reverse", reverse_command))
    application.add_handler(CommandHandler("slot", slot_command))
    application.add_handler(CommandHandler("coinflip", coinflip_command))
    application.add_handler(CommandHandler("meme", meme_command))
    application.add_handler(CommandHandler("geekjoke", geekjoke_command))
    application.add_handler(CommandHandler("dadjoke", dadjoke_command))
    application.add_handler(CommandHandler("dog", dog_command))
    application.add_handler(CommandHandler("affirmation", affirmation_command))
    application.add_handler(CommandHandler("advice", advice_command))
    application.add_handler(CommandHandler("gemini", gemini_command))
    application.add_handler(CommandHandler("imagine", imagine_command))
    application.add_handler(CommandHandler("yt", yt_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_event))

    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_click_handler))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()