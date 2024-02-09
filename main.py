import ast
import asyncio
import io
import json
import aiohttp
import aiosqlite
from pyrogram import Client, filters, types, errors
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import random
from Bard import AsyncChatbot
from dotenv import dotenv_values
import time
import praw
from tcp_latency import measure_latency
import google.generativeai as genai

# Load variables from the .env file
config = dotenv_values(".env")

api_id =  config.get("API_ID")
api_hash = config.get("API_HASH")

app = Client("my_bot", api_id=api_id, api_hash=api_hash)

@app.on_message(filters.command(""))
async def start(client: Client, message: types.Message):
    print(message.text)

@app.on_message(filters.command("start"))
async def start(client: Client, message: types.Message):
    await message.reply(f"Hello {message.from_user.first_name}, My name is Shin and I'm developed by @Shinobi7k.\nI'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me.")

@app.on_message(filters.command("help"))
async def help(client: Client, message: types.Message):
    await message.reply(
"""Whether it's using free AI tools, searching internet or just having fun, I will surely come in handy.
\nHere's my commands list:
/gemini - Chat with Google's Gemini Pro AI
/imagine - Generate AI images
/search - Google it without leaving the chat
/anime - Search Anime
/manga - Search Manga
/ln - Search Light Novels
/character - Search Anime & Manga characters
/timer - Set yourself a timer
/meme - Get a random meme from Reddit
/dadjoke - Get a random dad joke
/geekjoke - Get a random geek joke
/advice - Get a random advice
/affirmation - Get a random affirmation
/dog - Get a random dog pic/vid/gif
/aghpb - Anime girl holding programming book
/slot - A slot game
/coinflip - Flip a coin
/reverse - Reverse your words
/echo - Repeats your words
/ping - Get bot's latency
\n__Developed with 💙 by @Shinobi7k__"""
)

@app.on_message(filters.command("character"))
async def character(client: Client, message: types.Message):
    query = message.text.replace("/character", "").replace("@shinobi7kbot", "").strip()
    if query == "": return await message.reply("Please provide a search query.")
    index = 0
    character_results_list = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.jikan.moe/v4/characters?q={query}&order_by=favorites&sort=desc") as response:
            results = await response.json()
            print(results)
    for result in results['data']:
        this_result_dict = {}
        url = result["url"]
        this_result_dict['url'] = url
        image_url = result["images"]["jpg"]["image_url"]
        this_result_dict['image_url'] = image_url
        name = result["name"]
        this_result_dict['name'] = name
        favorites = result["favorites"]
        this_result_dict['favorites'] = favorites
        about = result["about"]
        print(about)
        if len(str(about)) > 800: about = about[:800] + "..."
        this_result_dict['about'] = about
        character_results_list.append(this_result_dict)
        index += 1
        if index == 10: break
        buttons = InlineKeyboardMarkup(
        [
            # [
            #     InlineKeyboardButton("Previous", callback_data=f"characterprev"),
            #     InlineKeyboardButton("Next", callback_data=f"characternext")
            # ],
            [
                InlineKeyboardButton("Open in MAL", url=character_results_list[0]['url'])
            ]
        ]
    )
   
    if index == 0: return await message.reply("No results found.")
    else: my_msg = await message.reply_photo(photo=character_results_list[0]['image_url'], reply_markup=buttons,
# caption=f"""__**{1}**__
caption=f"""
**🎗️ Name:** {character_results_list[0]['name']}
**⭐ Favorites:** {character_results_list[0]['favorites']}
**👓 About:** {character_results_list[0]['about']}""")
    async with aiosqlite.connect("database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("CREATE TABLE IF NOT EXISTS character (message_id TEXT, current_index INTEGER, character_result_list TEXT)")
            await cursor.execute("INSERT INTO character (message_id, current_index, character_result_list) VALUES (?, ?, ?)", (my_msg.id, 0, str(character_results_list)))
            await connection.commit()


@app.on_message(filters.command("manga"))
async def manga(client: Client, message: types.Message):
    query = message.text.replace("/manga", "").replace("@shinobi7kbot", "").strip()
    if query == "": return await message.reply("Please provide a search query.")
    index = 0
    manga_results_list = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.jikan.moe/v4/manga?q={query}&order_by=favorites&sort=desc") as response:
            results = await response.json()
    for result in results['data']:
        this_result_dict = {}
        url = result["url"]
        this_result_dict['url'] = url
        image_url = result["images"]["jpg"]["large_image_url"]
        this_result_dict['image_url'] = image_url
        title = result["title"]
        this_result_dict['title'] = title
        chapters = result["chapters"]
        this_result_dict['chapters'] = chapters
        the_type = result["type"]
        this_result_dict['the_type'] = the_type
        year = result["published"]["prop"]["from"]["year"]
        this_result_dict['year'] = year
        score = result["score"]
        this_result_dict['score'] = score
        themes = []
        for theme in result["themes"]:
            themes.append(theme["name"])
        themes = str(themes).replace("[", "").replace("]", "").replace("'", "")
        this_result_dict['themes'] = themes
        genres = []
        for studio in result["genres"]:
            genres.append(studio["name"])
        genres = str(genres).replace("[", "").replace("]", "").replace("'", "")
        this_result_dict['genres'] = genres
        manga_results_list.append(this_result_dict)
        index += 1
        if index == 10: break
        buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Previous", callback_data=f"mangaprev"),
                InlineKeyboardButton("Next", callback_data=f"manganext")
            ],
            [
                InlineKeyboardButton("Open in MAL", url=manga_results_list[0]['url'])
            ]
        ]
    )
   
    if index == 0: return await message.reply("No results found.")
    else: my_msg = await message.reply_photo(photo=manga_results_list[0]['image_url'], reply_markup=buttons,
caption=f"""__**{1}**__
**🎗️ Title:** {manga_results_list[0]['title']}
**👓 Type:** {manga_results_list[0]['the_type']}
**⭐ Score:** {manga_results_list[0]['score']}
**📃 Chapters:** {manga_results_list[0]['chapters']}
**📅 Year:** {manga_results_list[0]['year']}
**🎆 Themes: **{manga_results_list[0]['themes']}
**🎞️ Genres:** {manga_results_list[0]['genres']}""")
    async with aiosqlite.connect("database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("CREATE TABLE IF NOT EXISTS manga (message_id TEXT, current_index INTEGER, manga_result_list TEXT)")
            await cursor.execute("INSERT INTO manga (message_id, current_index, manga_result_list) VALUES (?, ?, ?)", (my_msg.id, 0, str(manga_results_list)))
            await connection.commit()


@app.on_message(filters.command("anime"))
async def anime(client: Client, message: types.Message):
    query = message.text.replace("/anime", "").replace("@shinobi7kbot", "").strip()
    if query == "": return await message.reply("Please provide a search query.")
    index = 0
    anime_results_list = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.jikan.moe/v4/anime?q={query}&order_by=favorites&sort=desc") as response:
            results = await response.json()
    for result in results['data']:
        this_result_dict = {}
        url = result["url"]
        this_result_dict['url'] = url
        image_url = result["images"]["jpg"]["large_image_url"]
        this_result_dict['image_url'] = image_url
        trialer = result["trailer"]["url"]
        this_result_dict['trailer'] = trialer
        title = result["title"]
        this_result_dict['title'] = title
        source = result["source"]
        this_result_dict['source'] = source
        episodes = result["episodes"]
        this_result_dict['episodes'] = episodes
        the_type = result["type"]
        this_result_dict['the_type'] = the_type
        year = result["aired"]["prop"]["from"]["year"]
        this_result_dict['year'] = year
        score = result["score"]
        this_result_dict['score'] = score
        themes = []
        for theme in result["themes"]:
            themes.append(theme["name"])
        themes = str(themes).replace("[", "").replace("]", "").replace("'", "")
        this_result_dict['themes'] = themes
        studios = []
        for studio in result["studios"]:
            studios.append(studio["name"])
        studios = str(studios).replace("[", "").replace("]", "").replace("'", "")
        this_result_dict['studios'] = studios
        genres = []
        for studio in result["genres"]:
            genres.append(studio["name"])
        genres = str(genres).replace("[", "").replace("]", "").replace("'", "")
        this_result_dict['genres'] = genres
        anime_results_list.append(this_result_dict)
        index += 1
        if index == 10: break
    if anime_results_list[0]['trailer'] == None:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Previous", callback_data=f"animeprev"),
                    InlineKeyboardButton("Next", callback_data=f"animenext")
                ],
                [
                    InlineKeyboardButton("Open in MAL", url=anime_results_list[0]['url'])
                ]
            ]
        )
    else:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Previous", callback_data=f"animeprev"),
                    InlineKeyboardButton("Next", callback_data=f"animenext")
                ],
                [
                    InlineKeyboardButton("Open in MAL", url=anime_results_list[0]['url'])
                ],
                [
                    InlineKeyboardButton("Watch Trailer", url=anime_results_list[0]['trailer'])
                ]
            ]
        )
    if index == 0: return await message.reply("No results found.")
    else: my_msg = await message.reply_photo(photo=anime_results_list[0]['image_url'], reply_markup=buttons,
caption=f"""__**{1}**__
**🎗️ Title:** {anime_results_list[0]['title']}
**👓 Type:** {anime_results_list[0]['the_type']}
**⭐ Score:** {anime_results_list[0]['score']}
**📃 Episodes:** {anime_results_list[0]['episodes']}
**📅 Year:** {anime_results_list[0]['year']}
**🎆 Themes: **{anime_results_list[0]['themes']}
**🎞️ Genres:** {anime_results_list[0]['genres']}
**🏢 Studio:** {anime_results_list[0]['studios']}
**🧬 Source:** {anime_results_list[0]['source']}""")
    async with aiosqlite.connect("database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("CREATE TABLE IF NOT EXISTS anime (message_id TEXT, current_index INTEGER, anime_result_list TEXT)")
            await cursor.execute("INSERT INTO anime (message_id, current_index, anime_result_list) VALUES (?, ?, ?)", (my_msg.id, 0, str(anime_results_list)))
            await connection.commit()

@app.on_callback_query()
async def button_click_handler(client: Client, query: types.CallbackQuery):
    data = query.data
    if data.startswith("anime"):
        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(f"SELECT * FROM anime WHERE message_id = {query.message.id}") # SELECT * FROM a WHERE id = ?;
                db_data = await cursor.fetchall()
        current_index = db_data[0][1]
        anime_results_list = ast.literal_eval(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
        if "prev" in data: btn_type = "prev"
        elif "next" in data: btn_type = "next"
        prev_index = 0
        next_index = 0
        if current_index == 0:
            prev_index = 0
            next_index = 1
        elif current_index == 4:
            prev_index = 3
            next_index = 4
        else:
            prev_index = current_index - 1
            next_index = current_index + 1

        updated_index = 0
        if btn_type == "prev":
            updated_index = prev_index
        elif btn_type == "next":
            updated_index = next_index

        if updated_index == current_index: return await query.answer()

        image_link = anime_results_list[updated_index]['image_url']
        message_content = f"""__**{updated_index + 1}**__
**🎗️ Title:** {anime_results_list[updated_index]['title']}
**👓 Type:** {anime_results_list[updated_index]['the_type']}
**⭐ Score:** {anime_results_list[updated_index]['score']}
**📃 Episodes:** {anime_results_list[updated_index]['episodes']}
**📅 Year:** {anime_results_list[updated_index]['year']}
**🎆 Themes: **{anime_results_list[updated_index]['themes']}
**🎞️ Genres:** {anime_results_list[updated_index]['genres']}
**🏢 Studio:** {anime_results_list[updated_index]['studios']}
**🧬 Source:** {anime_results_list[updated_index]['source']}"""
        if anime_results_list[updated_index]['trailer'] == "None":
            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Previous", callback_data=f"animeprev"),
                        InlineKeyboardButton("Next", callback_data=f"animenext")
                    ],
                    [
                        InlineKeyboardButton("Open in MAL", url=anime_results_list[updated_index]['url']),
                    ]
                ]
            )
        else:
            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Previous", callback_data=f"animeprev"),
                        InlineKeyboardButton("Next", callback_data=f"animenext")
                    ],
                    [
                        InlineKeyboardButton("Open in MAL", url=anime_results_list[updated_index]['url']),
                    ],
                    [
                        InlineKeyboardButton("Watch Trailer", url=anime_results_list[updated_index]['trailer'])
                    ]
                ]
            )

        await query.message.edit_media(media=types.InputMediaPhoto(media=image_link,caption=message_content))
        await query.message.edit_reply_markup(reply_markup=buttons)
        await query.answer()

        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                sql_query = "UPDATE anime SET current_index = ? WHERE message_id = ?"
                await cursor.execute(sql_query, (updated_index, str(query.message.id)))
                await connection.commit()

    elif data.startswith("manga"):
        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(f"SELECT * FROM manga WHERE message_id = {query.message.id}") # SELECT * FROM a WHERE id = ?;
                db_data = await cursor.fetchall()
        current_index = db_data[0][1]
        manga_results_list = ast.literal_eval(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
        if "prev" in data: btn_type = "prev"
        elif "next" in data: btn_type = "next"
        prev_index = 0
        next_index = 0
        if current_index == 0:
            prev_index = 0
            next_index = 1
        elif current_index == 4:
            prev_index = 3
            next_index = 4
        else:
            prev_index = current_index - 1
            next_index = current_index + 1

        updated_index = 0
        if btn_type == "prev":
            updated_index = prev_index
        elif btn_type == "next":
            updated_index = next_index

        if updated_index == current_index: return await query.answer()

        image_link = manga_results_list[updated_index]['image_url']
        message_content = f"""__**{updated_index + 1}**__
**🎗️ Title:** {manga_results_list[updated_index]['title']}
**👓 Type:** {manga_results_list[updated_index]['the_type']}
**⭐ Score:** {manga_results_list[updated_index]['score']}
**📃 Chapters:** {manga_results_list[updated_index]['chapters']}
**📅 Year:** {manga_results_list[updated_index]['year']}
**🎆 Themes: **{manga_results_list[updated_index]['themes']}
**🎞️ Genres:** {manga_results_list[updated_index]['genres']}"""
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Previous", callback_data=f"mangaprev"),
                    InlineKeyboardButton("Next", callback_data=f"manganext")
                ],
                [
                    InlineKeyboardButton("Open in MAL", url=manga_results_list[updated_index]['url']),
                ]
            ]
        )

        await query.message.edit_media(media=types.InputMediaPhoto(media=image_link,caption=message_content))
        await query.message.edit_reply_markup(reply_markup=buttons)
        await query.answer()

        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                sql_query = "UPDATE manga SET current_index = ? WHERE message_id = ?"
                await cursor.execute(sql_query, (updated_index, str(query.message.id)))
                await connection.commit()

    elif data.startswith("character"):
        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(f"SELECT * FROM character WHERE message_id = {query.message.id}") # SELECT * FROM a WHERE id = ?;
                db_data = await cursor.fetchall()
        current_index = db_data[0][1]
        print(f"db_data[0][2] {db_data[0][2]}")
        character_results_list = json.loads(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
        if "prev" in data: btn_type = "prev"
        elif "next" in data: btn_type = "next"
        prev_index = 0
        next_index = 0
        if current_index == 0:
            prev_index = 0
            next_index = 1
        elif current_index == 4:
            prev_index = 3
            next_index = 4
        else:
            prev_index = current_index - 1
            next_index = current_index + 1

        updated_index = 0
        if btn_type == "prev":
            updated_index = prev_index
        elif btn_type == "next":
            updated_index = next_index

        if updated_index == current_index: return await query.answer()

        image_link = character_results_list[updated_index]['image_url']
        message_content = f"""__**{updated_index + 1}**__
**🎗️ Title:** {character_results_list[updated_index]['title']}
**⭐ Favorites:** {character_results_list[updated_index]['favorites']}
**👓 About:** {character_results_list[updated_index]['about']}"""
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Previous", callback_data=f"characterprev"),
                    InlineKeyboardButton("Next", callback_data=f"characternext")
                ],
                [
                    InlineKeyboardButton("Open in MAL", url=character_results_list[updated_index]['url']),
                ]
            ]
        )

        await query.message.edit_media(media=types.InputMediaPhoto(media=image_link,caption=message_content))
        await query.message.edit_reply_markup(reply_markup=buttons)
        await query.answer()

        async with aiosqlite.connect("database.db") as connection:
            async with connection.cursor() as cursor:
                sql_query = "UPDATE character SET current_index = ? WHERE message_id = ?"
                await cursor.execute(sql_query, (updated_index, str(query.message.id)))
                await connection.commit()


@app.on_message(filters.command("aghpb"))
async def aghpb(client: Client, message: types.Message):
    url = "https://api.devgoldy.xyz/aghpb/v1/random"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            image_bytes = await response.read()
    with io.BytesIO(image_bytes) as image_file: # converts to file-like object
        await message.reply_photo(image_file)

@app.on_message(filters.command("echo"))
async def echo(client: Client, message: types.Message):
    await message.reply(message.text.replace("/echo", "").replace("@shinobi7kbot", ""))

@app.on_message(filters.command("ping"))
async def ping(client: Client, message: types.Message):
    initial_latency = int(measure_latency(host='telegram.org')[0])
    start_time = time.time()
    sent_message = await message.reply("...")
    end_time = time.time()
    round_latency = int((end_time - start_time) * 1000)
    await sent_message.edit(f"Pong!\nInitial response: `{initial_latency}ms`\nRound-trip: `{round_latency}ms`")

@app.on_message(filters.command("timer"))
async def timer(client: Client, message: types.Message):
    time = message.text.replace("/timer", "").replace("@shinobi7kbot", "").strip()
    if time == "": return await message.reply("Type time and time unit (s,m,h,d,w,y).")
    get_time = {
    "s": 1, "m": 60, "h": 3600, "d": 86400,
    "w": 604800, "mo": 2592000, "y": 31104000 }
    time_unit = time[-1]
    time_unit_number = get_time.get(time_unit)
    input_number = time[:-1]
    try: int(input_number)
    except: return await message.reply("Type time and time unit (s,m,h,d,w,y) correctly.")
    try:
        sleep = int(time_unit_number) * int(input_number)
        if time_unit == "s": time_unit = "seconds"
        elif time_unit == "m": time_unit = "minutes"
        elif time_unit == "h": time_unit = "hours"
        elif time_unit == "d": time_unit = "days"
        elif time_unit == "w": time_unit = "weeks"
        elif time_unit == "mo": time_unit = "months"
        elif time_unit == "y": time_unit = "years"
        await message.reply(f"Timer set to {input_number} {time_unit}.")
    except: return await message.reply("Type time and time unit (s,m,h,d,w,y) correctly.")
    await asyncio.sleep(sleep)
    await message.reply("Time over")

@app.on_message(filters.command("imagine"))
async def imagine(client: Client, message: types.Message):
    something_to_imagine = message.text.replace("/imagine", "").replace("@shinobi7kbot", "").strip()
    if something_to_imagine == "": return await message.reply("You have to descripe the image.")
    waiting_msg = await message.reply("Wait a moment...")
    API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
    API_TOKEN = config.get("HUGGINGFACE_TOKEN")
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    payload = {"inputs": f"{something_to_imagine}, mdjrny-v4 style"}
    async with aiohttp.ClientSession(headers = headers) as session:
        async with session.post(API_URL, json = payload) as response:
            image_bytes =  await response.read()
    with io.BytesIO(image_bytes) as file:
        await message.reply_photo(file)
    await waiting_msg.delete()

@app.on_message(filters.command("search"))
async def search(client: Client, message: types.Message):
    something_to_search = message.text.replace("/search", "").replace("@shinobi7kbot", "").strip()
    if something_to_search == "": return await message.reply("Type something to search.")
    waiting_msg = await message.reply("Wait a moment...")
    api_key = config.get("WIBU_API_KEY")
    url = "https://wibu-api.eu.org/api/google/search"
    params = {
        'query': something_to_search,
        'x_wibu_key': api_key
    }
    headers = {
        'accept': 'application/json',
        'X-WIBU-Key': api_key
    }
    timeout =   aiohttp.ClientTimeout(total=None,sock_connect=30,sock_read=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url=url, headers=headers, params=params) as response:
            results = await response.json()
    index = 0
    results_message = ""
    try:
        for result in results['result']:
            index += 1
            title = result['title']
            link = result['link']
            snippet = result['snippet']
            results_message = results_message + f"**[{title}]({link})**\n- {snippet}\n\n"
            if index == 10: break
        await message.reply(results_message)
    except Exception as e:
        print(e)
        await message.reply("Results not found.")
    await waiting_msg.delete()

@app.on_message(filters.command("ln"))
async def ln(client: Client, message: types.Message):
    ln_name = message.text.replace("/ln", "").replace("@shinobi7kbot", "").strip()
    if ln_name == "": return await message.reply("Type LN title.")
    waiting_msg = await message.reply("Wait a moment...")
    api_key = config.get("WIBU_API_KEY")
    url = "https://wibu-api.eu.org/api/novel/novelupdates/search"
    params = {
        'query': ln_name,
        'x_wibu_key': api_key
    }
    headers = {
        'accept': 'application/json',
        'X-WIBU-Key': api_key
    }
    timeout =   aiohttp.ClientTimeout(total=None,sock_connect=30,sock_read=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url=url, headers=headers, params=params) as response:
            results = await response.json()
    index = 0
    try:
        for result in results['result']:
            await message.reply_photo(photo=result['img'], caption=f"- **Title:** {result['title']}\n- **Chapters:** {result['chapter']}\n- **Tags:** {result['tags']}\n- **URL:** {result['url']}")
            index += 1
            if index == 5: break
    except Exception as e:
        print(e)
        await message.reply("LN not found.")
    await waiting_msg.delete()

@app.on_message(filters.command("reverse"))
async def reverse(client: Client, message: types.Message):
    your_words = message.text.replace("/reverse", "").replace("@shinobi7kbot", "").strip()
    if your_words == "": return await message.reply("Type some words.")
    t_rev = your_words[::-1].replace("@", "@\u200B").replace("&", "&\u200B")
    await message.reply(f"🔁 {t_rev}")

@app.on_message(filters.command("slot"))
async def slot(client: Client, message: types.Message):
    emojis = "🍎🍊🍐🍋🍉🍇🍓🍒"
    a, b, c = [random.choice(emojis) for g in range(3)]
    slotmachine = f"**[ {a} {b} {c} ]\n{message.from_user.first_name}**,"
    if (a == b == c): await message.reply(f"{slotmachine} All matching, you won! 🎉")
    elif (a == b) or (a == c) or (b == c): await message.reply(f"{slotmachine} 2 in a row, you won! 🎉")
    else: await message.reply(f"{slotmachine} No match, you lost 😢")

@app.on_message(filters.command("coinflip"))
async def coinflip(client: Client, message: types.Message):
    coinsides = ["Heads", "Tails"]
    await message.reply(f"**{message.from_user.first_name}** flipped a coin and got **{random.choice(coinsides)}**!")

@app.on_message(filters.command("meme"))
async def meme(client: Client, message: types.Message):
    reddit = praw.Reddit(
        client_id = config.get("REDDIT_CLIENT_ID"),
        client_secret = config.get("REDDIT_CLIENT_SECRET"),
        user_agent = "ShinobiBot",
        check_for_async = False
        )
    subreddit = reddit.subreddit("Animemes")
    all_subs = []
    hot = subreddit.hot(limit=50)
    for submission in hot:
        all_subs.append(submission)
        random_sub = random.choice(all_subs)
        name = random_sub.title
        url = random_sub.url
    if ".gif" in url: await message.reply_animation(url, caption=name)
    elif ".mp4" in url: await message.reply_video(url, caption=name)
    else: await message.reply_photo(url, caption=name)

@app.on_message(filters.command("geekjoke"))
async def geekjoke(client: Client, message: types.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://geek-jokes.sameerkumar.website/api?format=json") as response:
            data = await response.json()
    joke = data['joke']
    await message.reply(joke)

@app.on_message(filters.command("dadjoke"))
async def dadjoke(client: Client, message: types.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://icanhazdadjoke.com/slack") as response:
            data = await response.json()
    joke = data['attachments'][0]['text']
    await message.reply(joke)

@app.on_message(filters.command("dog"))
async def dog(client: Client, message: types.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://random.dog/woof.json") as response:
            data = await response.json()
    dog_url = data['url']
    if dog_url.endswith(".mp4"): return await message.reply_video(dog_url)
    elif dog_url.endswith(".jpg") or dog_url.endswith(".png"): return await message.reply_photo(dog_url)
    elif dog_url.endswith(".gif"): return await message.reply_animation(dog_url)

@app.on_message(filters.command("affirmation"))
async def affirmation(client: Client, message: types.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://www.affirmations.dev/") as response:
            data = await response.json()
    affirmation = data['affirmation']
    await message.reply(affirmation)

@app.on_message(filters.command("advice"))
async def advice(client: Client, message: types.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.adviceslip.com/advice") as response:
            data = await response.json(content_type="text/html")
    advice = data['slip']['advice']
    await message.reply(advice)

@app.on_message(filters.command("bard"))
async def bard(client: Client, message: types.Message):
    # BARD_1PSID = config.get("BARD_1PSID")
    # BARD_1PSIDCC = config.get("BARD_1PSIDCC")
    # prompt = message.text.replace("/bard", "").replace("@shinobi7kbot", "").strip()
    # if prompt == "": return await message.reply("Please write your question on the same message.")
    # try:
    #     bard = await AsyncChatbot.create(BARD_1PSID, BARD_1PSIDCC)
    #     response = await bard.ask(prompt)
    #     images = response['images']
    #     response = response['content']
    #     images_list = []
    #     if images != set():
    #         for image in images:
    #             images_list.append(types.InputMediaPhoto(image))
    #     limit = 4000
    #     if len(response) > limit:
    #         result = [response[i: i + limit] for i in range(0, len(response), limit)]
    #         for half in result: msg = await message.reply(f"Bard: {half}")
    #     else: msg = await message.reply(f"Bard: {response}")
    #     if images_list != []: await message.reply_media_group(media=images_list, reply_to_message_id=msg.id)
    # except Exception as e:
    #     print(f"Bard error: {e}")
    #     await message.reply("Sorry, an unexpected error had occured.")
    prompt = message.text.replace("/bard", "").replace("@shinobi7kbot", "").strip()
    api_key = config.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    response = await model.generate_content_async(prompt)
    await message.reply(f"Gemini Pro: {response.text}")

@app.on_message(filters.command("gemini"))
async def bard(client: Client, message: types.Message):
    prompt = message.text.replace("/gemini", "").replace("@shinobi7kbot", "").strip()
    api_key = config.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    response = await model.generate_content_async(prompt)
    await message.reply(f"Gemini Pro: {response.text}")


@app.on_message(filters.text)
async def message_event(client: Client, message: types.Message):
    # تثبيحات
    if message.text.startswith("ثبح ") or message.text == "ثبح": await message.reply("ثباحو")
    elif message.text.startswith("ثباحو ") or message.text == "ثباحو": await message.reply("ثبح")
    elif message.text.startswith("مثائو ") or message.text == "مثائو": await message.reply("مثا")
    elif message.text.startswith("مثا ") or message.text == "مثا": await message.reply("مثائو")

    # يالبوت
    if "يالبوت" in message.text:
        normal_responses = [
                "اكيد يسطا" , "اكيد يبرو" , "بدون شك" , "يب اكيد" , "طبعا" , "اومال" , "ايوه" ,
                "يب" , "يب يب" , "اتكل علي الله يعم" , "مش فايقلك" ,
                "هي دي محتاجه سؤال!؟" , "لا" , "انا بقولك لا" , "اكيد لا" , "نوب" , "معرفش" ,
                "اكيد يغالي" , "اكيد ينقم" , "لا هه" , "صدقني انا ذات نفسي معرفش" , "انا لو أعرف هقولك"]
        hellos = ["نعم" , "نعم يغالي" , "نعم ينقم" , "عايز ايه" , "نعم يخويا"]
        steins_keys = ["stein" , "شتاين" , "ستاين"]
        steins = ["شتاينز الأعظم" , "شتاينز فوق" , "شتاينز فوق مستوي التقييم البشري" , "شتاينز اعظم انمي"]
        shinobi_keywords = ["shinobi" , "شنوبي" , "شنبي" , "شنوب" , "شينوبي"]
        father = ["شنوبي ابويا وعمي وعم عيالي" , "شنبي ابويا وعمي" , "شنوبي احسن اب في العالم"]
        azab = ["ده حنين عليا خالث" , "بابا شنبي مش بيمد ايده عليا" , "مش بيلمسني"]
        tabla = ["لا طبعا يغالي" , "شنوبي عمي وعم عيالي" , "شنوبي عمك" , "شنوبي فوق"]
        love = ["حبك" , "حبق" , "وانا كمان يغالي" , "+1"]
        win = ["مش هتكسب هه" , "نصيبك مش هتكسب" , "انا بقولك لا" , "على ضمانتي"]
        elhal = ["الحمدلله يخويا", "الحمدلله يغالي", "تمام الحمدلله"]

        #me responses
        if "انا" in message.text:
            if message.from_user.username == "Shinobi7k":
                if "ابوك" in message.text: return await message.reply(f"{random.choice(father)}")
        #shinobi responses
        for word in shinobi_keywords:
            if word in message.text:
                if "ابوك" in message.text: return await message.reply(f"{random.choice(father)}")
                if "بيعذبك" in message.text: return await message.reply(f"{random.choice(azab)}")
                if "بتطبل" in message.text: return await message.reply(f"{random.choice(tabla)}")
        #steins responses
        for word in steins_keys:
            if word in message.text: return await message.reply(f"{random.choice(steins)}")
        #exceptions
        if "هكسب" in message.text: return await message.reply(f"{random.choice(win)}")
        if "حبك" in message.text or "حبق" in message.text: return await message.reply(f"{random.choice(love)}")
        if "عامل ايه" in message.text or "عامل إيه" in message.text or "كيف حالك" in message.text: return await message.reply(f"{random.choice(elhal)}")
        #normal respones
        if " " in message.text: await message.reply(f"{random.choice(normal_responses)}")
        #hellos responses
        else: return await message.reply(f"{random.choice(hellos)}")


print("I'm running")
app.run()