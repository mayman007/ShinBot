import asyncio
import io
import aiohttp
from pyrogram import Client, filters, types
import random
from Bard import AsyncChatbot
from dotenv import dotenv_values
import time
import httpx
import praw
from tcp_latency import measure_latency
# from jikanpy import AioJikan

# Load variables from the .env file
config = dotenv_values(".env")

api_id =  config.get("API_ID")
api_hash = config.get("API_HASH")

app = Client("my_bot", api_id=api_id, api_hash=api_hash)

@app.on_message(filters.command("start"))
async def start(client: Client, message: types.Message):
    await message.reply(f"Hello {message.from_user.first_name}, My name is Shin and I'm developed by @Shinobi7k.\nI'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me.")

@app.on_message(filters.command("help"))
async def help(client: Client, message: types.Message):
    await message.reply(
"""Whether it's using free AI tools, searching internet or just having fun, I will surely come in handy.
\nHere's my commands list:
/bard - Chat with Bard AI
/imagine - Generate AI images
/search - Google it without leaving the chat
/anime - Search Anime
/ln - Search Light Novels
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

@app.on_message(filters.command("anime"))
async def amime(client: Client, message: types.Message):
    query = message.text.replace("/anime", "").replace("@shinobi7kbot", "").strip()
    if query == "": return await message.reply("Please provide a search query.")
    index = 0
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.jikan.moe/v4/anime?q={query}") as response:
            results = await response.json()
        for result in results['data']:
            url = result["url"]
            image_url = result["images"]["jpg"]["large_image_url"]
            trialer = result["trailer"]["url"]
            title = result["title"]
            source = result["source"]
            episodes = result["episodes"]
            the_type = result["type"]
            year = result["aired"]["prop"]["from"]["year"]
            score = result["score"]
            themes = []
            for theme in result["themes"]:
                themes.append(theme["name"])
            themes = str(themes).replace("[", "").replace("]", "").replace("'", "")
            studios = []
            for studio in result["studios"]:
                studios.append(studio["name"])
            studios = str(studios).replace("[", "").replace("]", "").replace("'", "")
            genres = []
            for studio in result["genres"]:
                genres.append(studio["name"])
            genres = str(genres).replace("[", "").replace("]", "").replace("'", "")
            index += 1
            if trialer == None:
                buttons = types.InlineKeyboardMarkup(
                [
                    [
                        types.InlineKeyboardButton("Open in MAL", url=url)
                    ]
                ]
                )
            else:
                buttons = types.InlineKeyboardMarkup(
                [
                    [
                        types.InlineKeyboardButton("Open in MAL", url=url)
                    ],
                    [
                        types.InlineKeyboardButton("Watch Trailer", url=trialer)
                    ]
                ]
                )
            await message.reply_photo(photo=image_url, reply_markup=buttons, caption=f"**🎗️ Title:** {title}\n**👓 Type:** {the_type}\n**⭐ Score:** {score}\n**📃 Episodes:** {episodes}\n**📅 Year:** {year}\n**🎆 Themes: **{themes}\n**🎞️ Genres:** {genres}\n**🏢 Studio:** {studios}\n**🧬 Source:** {source}")
            if index == 5: break
    if index == 0: await message.reply("No results found.")

@app.on_message(filters.command("aghpb"))
async def aghpb(client: Client, message: types.Message):
    url = "https://api.devgoldy.xyz/aghpb/v1/random"
    async with httpx.AsyncClient() as session:
        response = await session.get(url=url)
        image_bytes = response.read()
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

# @app.on_message(filters.command("character"))
# async def character(client: Client, message: types.Message):
#     name = message.text.replace("/character", "").replace("@shinobi7kbot", "").strip()
#     print(name)
#     if name == "": return await message.reply("Type character name.")
#     waiting_msgs_list = ['Searching for something nice...", "Wait a moment...", "Fetching...']
#     waiting_msg = await message.reply(random.choice(waiting_msgs_list))
#     nekos = NekosAPI()
#     characters = nekos.get_characters(limit=10, offset=0, search=f"%?{name}%?")
#     for character in characters:
#         print(character)
#         character_ages = ""
#         for age in character.ages:
#             character_ages = f"{character_ages}{age}, "
#         character_ages = character_ages[:-2]
#         character_occupations = ""
#         for occupation in character.occupations:
#             character_occupations = f"{character_occupations}{occupation}, "
#         character_occupations = character_occupations[:-2]
#         await message.reply(f"- **Name:** {character.name}\n- **Source:** {character.source}\n- **Age:** {character_ages} ({character.birth_date})\n- **Gender:** {character.gender}\n- **Nationality:** {character.nationality}\n- **Occupations:** {character_occupations}\n- **Description:** {character.description}")
    # await waiting_msg.delete()

@app.on_message(filters.command("imagine"))
async def imagine(client: Client, message: types.Message):
    something_to_imagine = message.text.replace("/imagine", "").replace("@shinobi7kbot", "").strip()
    if something_to_imagine == "": return await message.reply("You have to descripe the image.")
    waiting_msg = await message.reply("Wait a moment...")
    api_key = config.get("WIBU_API_KEY")
    url = "https://wibu-api.eu.org/api/ai/midjourney"
    params = {
        'query': something_to_imagine,
        'x_wibu_key': api_key
    }
    headers = {
        'accept': 'application/json',
        'X-WIBU-Key': api_key
    }
    timeout = httpx.Timeout(30.0, connect=60.0)
    async with httpx.AsyncClient(timeout=timeout) as session:
        response = await session.get(url=url, headers=headers, params=params)
    image_bytes = response.read()
    with io.BytesIO(image_bytes) as image_file: # converts to file-like object
        await message.reply_photo(image_file)
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
    timeout = httpx.Timeout(30.0, connect=60.0)
    async with httpx.AsyncClient(timeout=timeout) as session:
        response = await session.get(url=url, headers=headers, params=params)
    results = response.json()
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
    timeout = httpx.Timeout(30.0, connect=60.0)
    async with httpx.AsyncClient(timeout=timeout) as session:
        response = await session.get(url=url, headers=headers, params=params)
    results = response.json()
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

# @app.on_message(filters.command("neko"))
# async def neko(client: Client, message: types.Message):
#     waiting_msgs_list = ['Searching for something nice...", "Wait a moment...", "Fetching...']
#     waiting_msg = await message.reply(random.choice(waiting_msgs_list))
#     nekos = NekosAPI()
#     image = nekos.get_random_image(categories=['kemonomimi'])
#     await message.reply_photo(image.url)
#     await waiting_msg.delete()

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
    async with httpx.AsyncClient() as session:
        response = await session.get("https://geek-jokes.sameerkumar.website/api?format=json")
    data = response.json()
    joke = data['joke']
    await message.reply(joke)

@app.on_message(filters.command("dadjoke"))
async def dadjoke(client: Client, message: types.Message):
    async with httpx.AsyncClient() as session:
        response = await session.get("https://icanhazdadjoke.com/slack")
    data = response.json()
    joke = data['attachments'][0]['text']
    await message.reply(joke)

@app.on_message(filters.command("dog"))
async def dog(client: Client, message: types.Message):
    async with httpx.AsyncClient() as session:
        response = await session.get("https://random.dog/woof.json")
    data = response.json()
    dog_url = data['url']
    if dog_url.endswith(".mp4"): return await message.reply_video(dog_url)
    elif dog_url.endswith(".jpg") or dog_url.endswith(".png"): return await message.reply_photo(dog_url)
    elif dog_url.endswith(".gif"): return await message.reply_animation(dog_url)

@app.on_message(filters.command("affirmation"))
async def affirmation(client: Client, message: types.Message):
    async with httpx.AsyncClient() as session:
        response = await session.get("https://www.affirmations.dev/")
    data = response.json()
    affirmation = data['affirmation']
    await message.reply(affirmation)

@app.on_message(filters.command("advice"))
async def advice(client: Client, message: types.Message):
    async with httpx.AsyncClient() as session:
        response = await session.get("https://api.adviceslip.com/advice")
    data = response.json()
    advice = data['slip']['advice']
    await message.reply(advice)

@app.on_message(filters.command("bard"))
async def bard(client: Client, message: types.Message):
    BARD_1PSID = config.get("BARD_1PSID")
    BARD_1PSIDCC = config.get("BARD_1PSIDCC")
    prompt = message.text.replace("/bard", "").replace("@shinobi7kbot", "").strip()
    if prompt == "": return await message.reply("Please write your question on the same message.")
    try:
        bard = await AsyncChatbot.create(BARD_1PSID, BARD_1PSIDCC)
        response = await bard.ask(prompt)
        images = response['images']
        response = response['content']
        if images != set():
            bard_images_counter = 0
            response = f"{response}\n\n"
            for image in images:
                bard_images_counter += 1
                response += f"\nImage {bard_images_counter}: {image}"
        limit = 1800
        if len(response) > limit:
            result = [response[i: i + limit] for i in range(0, len(response), limit)]
            for half in result: await message.reply(f"Bard: {half}")
        else: await message.reply(f"Bard: {response}")
    except Exception as e:
        print(f"Bard error: {e}")
        await message.reply("Sorry, an unexpected error had occured.")

@app.on_message(filters.text)
async def message_event(client: Client, message: types.Message):
    # تثبيحات
    if message.text.startswith("ثبح"): await message.reply("ثباحو")
    elif message.text.startswith("ثباحو"): await message.reply("ثبح")
    elif message.text.startswith("مثائو"): await message.reply("مثا")
    elif message.text.startswith("مثا"): await message.reply("مثائو")

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