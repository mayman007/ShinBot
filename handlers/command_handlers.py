import asyncio
import io
import aiohttp
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random
import time
import praw
from tcp_latency import measure_latency
import google.generativeai as genai
from config import BOT_USERNAME, ADMIN_ID, GEMINI_API_KEY, HUGGINGFACE_TOKEN, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from main import save_usage

# Usagedata command
async def usagedata_command(update: Update, context):
    if update.message.from_user.id == int(ADMIN_ID):
        async with aiosqlite.connect("db/usage.db") as connection:
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

# start command
async def start_command(update: Update, context):
    await update.message.reply_text(
        f"Hello {update.message.from_user.first_name}, My name is Shin and I'm developed by @Mayman007tg.\n"
        "I'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me."
    )

# help command
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

    async with aiosqlite.connect("db/database.db") as connection:
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
    query = text.replace("/manga", "").replace(f"@{BOT_USERNAME}", "").strip()
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
    async with aiosqlite.connect("db/database.db") as connection:
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
    query = text.replace("/anime", "").replace(f"@{BOT_USERNAME}", "").strip()
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

    async with aiosqlite.connect("db/database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "CREATE TABLE IF NOT EXISTS anime (message_id TEXT, current_index INTEGER, anime_result_list TEXT)"
            )
            await cursor.execute(
                "INSERT INTO anime (message_id, current_index, anime_result_list) VALUES (?, ?, ?)",
                (str(sent_msg.message_id), 0, str(anime_results_list))
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
    text = update.message.text.replace("/echo", "").replace(f"@{BOT_USERNAME}", "").strip()
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
    message_text = update.message.text.replace("/timer", "").replace(f"@{BOT_USERNAME}", "").strip()
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

    # async with aiosqlite.connect("db/database.db") as connection:
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

    your_words = update.message.text.replace("/reverse", "").replace(f"@{BOT_USERNAME}", "").strip()
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
        client_id = REDDIT_CLIENT_ID,
        client_secret = REDDIT_CLIENT_SECRET,
        user_agent = REDDIT_USER_AGENT,
        check_for_async = False
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
        prompt = update.message.text.replace("/gemini", "").replace(f"@{BOT_USERNAME}", "").strip()
        if prompt == "":
            await update.message.reply_text("Please write your prompt on the same message.")
            return

        api_key = GEMINI_API_KEY
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

    try:
        # Remove command and bot username from the message text.
        something_to_imagine = update.message.text.replace("/imagine", "").replace(f"@{BOT_USERNAME}", "").strip()
        if not something_to_imagine:
            await update.message.reply_text("You have to descripe the image.")
            return

        # Send a waiting message to the user
        waiting_msg = await update.message.reply_text("Wait a moment...")

        API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
        API_TOKEN = HUGGINGFACE_TOKEN
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        payload = {"inputs": f"{something_to_imagine}, mdjrny-v4 style"}

        # Send the request to the Hugging Face Inference API
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(API_URL, json=payload) as response:
                image_bytes = await response.read()

        # Convert the received bytes to a file-like object, set a filename, and send it
        file = io.BytesIO(image_bytes)
        file.name = "image.png"  # Set an appropriate filename and extension
        await update.message.reply_photo(photo=file)

        # Delete the waiting message
        await waiting_msg.delete()
    except:
        await update.message.reply_text("Sorry, I ran into an error.")