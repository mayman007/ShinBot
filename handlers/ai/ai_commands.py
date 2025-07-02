import asyncio
import google.generativeai as genai
import aiohttp
import io
from pyrogram import Client, types
from config import BOT_USERNAME, GEMINI_API_KEY, HUGGINGFACE_TOKEN
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
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
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

# ---------------------------
# Imagine Command Handler
# ---------------------------
async def imagine_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "imagine")
    try:
        something_to_imagine = message.text.replace("/imagine", "").replace(f"@{BOT_USERNAME}", "").strip()
        if not something_to_imagine:
            await message.reply("You have to describe the image.")
            return

        waiting_msg = await message.reply("Wait a moment...")
        API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
        API_TOKEN = HUGGINGFACE_TOKEN
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        payload = {"inputs": f"{something_to_imagine}, mdjrny-v4 style"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(API_URL, json=payload) as response:
                image_bytes = await response.read()
        file = io.BytesIO(image_bytes)
        file.name = "image.png"
        await client.send_photo(chat.id, file)
        await waiting_msg.delete()
    except Exception:
        await message.reply("Sorry, I ran into an error.")