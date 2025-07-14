import asyncio
import google.generativeai as genai
from pyrogram import Client, types
from config import BOT_USERNAME, GEMINI_API_KEY, GEMINI_MODEL
from utils.usage import save_usage

# ---------------------------
# Gemini Command Handler
# ---------------------------
async def gemini_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "gemini")
    try:
        prompt = message.text.replace("/gemini", "").replace(f"@{BOT_USERNAME}", "").strip()
        if prompt == "":
            await message.reply("Please write your prompt on the same message.")
            return
        api_key = GEMINI_API_KEY
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = await model.generate_content_async(prompt)
        print(response)
        response_text = response.text
        limit = 4000
        if len(response_text) > limit:
            parts = [response_text[i: i + limit] for i in range(0, len(response_text), limit)]
            for part in parts:
                await message.reply(f"Gemini Pro: {part}")
                await asyncio.sleep(0.5)
        else:
            await message.reply(f"Gemini Pro: {response_text}")
    except Exception as e:
        print(f"Gemini error: {e}")
        await message.reply("Sorry, an unexpected error had occured.")

