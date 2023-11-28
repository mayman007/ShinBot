import asyncio
from pyrogram import Client, filters, types
import random
from Bard import AsyncChatbot
from dotenv import dotenv_values
import time
import httpx
from anime_api.apis import NekosAPI

# Load variables from the .env file
config = dotenv_values(".env")

api_id =  config.get("API_ID")
api_hash = config.get("API_HASH")

app = Client("my_bot", api_id=api_id, api_hash=api_hash)

@app.on_message(filters.command("echo"))
async def echo(client: Client, message: types.Message):
    await message.reply(message.text.replace("/echo ", ""))

@app.on_message(filters.command("ping"))
async def ping(client: Client, message: types.Message):
    start_time = time.time()
    sent_message = await message.reply("...")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await sent_message.edit(f"Pong! Latency: {latency}ms")

@app.on_message(filters.command("timer"))
async def timer(client: Client, message: types.Message):
    time = message.text.replace("/timer ", "").strip()
    if time == "": return await message.reply("Type time and time unit [s,m,h,d,w,mo,y] correctly.")
    get_time = {
    "s": 1, "m": 60, "h": 3600, "d": 86400,
    "w": 604800, "mo": 2592000, "y": 31104000 }
    timer = time
    a = time[-1]
    b = get_time.get(a)
    c = time[:-1]
    try: int(c)
    except: return await message.reply("Type time and time unit [s,m,h,d,w,mo,y] correctly.")
    try:
        sleep = int(b) * int(c)
        await message.reply(f"Timer set to {timer}.")
    except: return await message.reply("Type time and time unit [s,m,h,d,w,mo,y] correctly.")
    await asyncio.sleep(sleep)
    await message.reply("Time over")

@app.on_message(filters.command("character"))
async def character(client: Client, message: types.Message):
    name = message.text.replace("/character", "").strip()
    print(name)
    if name == "": return await message.reply("Type character name.")
    waiting_msgs_list = ["Searching for something nice...", "Wait a moment...", "Fetching..."]
    waiting_msg = await message.reply(random.choice(waiting_msgs_list))
    nekos = NekosAPI()
    characters = nekos.get_characters(limit=10, offset=0, search=f"%?{name}%?")
    for character in characters:
        print(character)
        character_ages = ""
        for age in character.ages:
            character_ages = f"{character_ages}{age}, "
        character_ages = character_ages[:-2]
        character_occupations = ""
        for occupation in character.occupations:
            character_occupations = f"{character_occupations}{occupation}, "
        character_occupations = character_occupations[:-2]
        await message.reply(f"- **Name:** {character.name}\n- **Source:** {character.source}\n- **Age:** {character_ages} ({character.birth_date})\n- **Gender:** {character.gender}\n- **Nationality:** {character.nationality}\n- **Occupations:** {character_occupations}\n- **Description:** {character.description}")
    await waiting_msg.delete()

@app.on_message(filters.command("neko"))
async def neko(client: Client, message: types.Message):
    waiting_msgs_list = ["Searching for something nice...", "Wait a moment...", "Fetching..."]
    waiting_msg = await message.reply(random.choice(waiting_msgs_list))
    nekos = NekosAPI()
    image = nekos.get_random_image(categories=["kemonomimi"])
    await message.reply_photo(image.url)
    await waiting_msg.delete()

@app.on_message(filters.command("dog"))
async def dog(client: Client, message: types.Message):
    async with httpx.AsyncClient() as session:
        response = await session.get("https://random.dog/woof.json")
    data = response.json()
    dog_url = data["url"]
    if dog_url.endswith(".mp4"): return await message.reply_video(dog_url)
    elif dog_url.endswith(".jpg") or dog_url.endswith(".png"): return await message.reply_photo(dog_url)
    elif dog_url.endswith(".gif"): return await message.reply_animation(dog_url)

@app.on_message(filters.command("affirmation"))
async def affirmation(client: Client, message: types.Message):
    async with httpx.AsyncClient() as session:
        response = await session.get("https://www.affirmations.dev/")
    data = response.json()
    affirmation = data["affirmation"]
    await message.reply(affirmation)

@app.on_message(filters.command("advice"))
async def advice(client: Client, message: types.Message):
    async with httpx.AsyncClient() as session:
        response = await session.get("https://api.adviceslip.com/advice")
    data = response.json()
    advice = data["slip"]["advice"]
    await message.reply(advice)

@app.on_message(filters.command("bard"))
async def bard(client: Client, message: types.Message):
    BARD_1PSID = config.get("BARD_1PSID")
    BARD_1PSIDCC = config.get("BARD_1PSIDCC")
    prompt = message.text.replace("/bard", "").strip()
    if prompt == "": return await message.reply("Please write your question on the same message.")
    try:
        bard = await AsyncChatbot.create(BARD_1PSID, BARD_1PSIDCC)
        response = await bard.ask(prompt)
        print(response)
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
    elif message.text.startswith("مثا"): await message.reply("مثائو")
    elif message.text.startswith("مثائو"): await message.reply("مثا")

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