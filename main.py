from pyrogram import Client, filters, types
import random
from Bard import AsyncChatbot
from dotenv import dotenv_values

# Load variables from the .env file
config = dotenv_values(".env")

api_id =  config.get("API_ID")
api_hash = config.get("API_HASH")

app = Client("my_bot", api_id=api_id, api_hash=api_hash)

@app.on_message(filters.command("echo"))
async def echo(client: Client, message: types.Message):
    await message.reply(message.text.replace("/echo ", ""))

@app.on_message(filters.command("bard"))
async def bard(client: Client, message: types.Message):
    BARD_1PSID = config.get("BARD_1PSID")
    BARD_1PSIDCC = config.get("BARD_1PSIDCC")
    prompt = message.text.replace("/bard", "").strip()
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