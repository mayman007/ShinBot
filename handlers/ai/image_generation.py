import aiohttp
import io
from pyrogram import Client, types
from config import BOT_USERNAME, HUGGINGFACE_TOKEN
from utils.usage import save_usage

# Track active requests per chat
active_imagine_requests = set()

# ---------------------------
# Imagine Command Handler
# ---------------------------
async def imagine_command(client: Client, message: types.Message):
    chat = message.chat
    chat_id = chat.id

    # Limit to one request at a time per chat
    if chat_id in active_imagine_requests:
        await message.reply("Please wait for your previous image generation request to finish before sending another.")
        return
    active_imagine_requests.add(chat_id)

    await save_usage(chat, "imagine")
    try:
        something_to_imagine = message.text.replace("/imagine", "").replace(f"@{BOT_USERNAME}", "").strip()
        if not something_to_imagine:
            await message.reply("You have to describe the image.")
            active_imagine_requests.discard(chat_id)
            return

        waiting_msg = await message.reply("Wait a moment...")
        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        API_TOKEN = HUGGINGFACE_TOKEN
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        payload = {"inputs": something_to_imagine}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(API_URL, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"API Error: {response.status} - {error_text}")
                    await waiting_msg.edit(f"Failed to generate image. API Error {response.status}: {error_text}")
                    active_imagine_requests.discard(chat_id)
                    return
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    error_text = await response.text()
                    print(f"Invalid response type: {content_type}, Response: {error_text}")
                    await waiting_msg.edit(f"Image generation failed. Error: {error_text}")
                    active_imagine_requests.discard(chat_id)
                    return
                image_bytes = await response.read()
        
        file = io.BytesIO(image_bytes)
        file.name = "image.png"
        await message.reply_photo(file)
        await waiting_msg.delete()
    except Exception as e:
        print(f"Imagine Error: {e}")
        await message.reply(f"Sorry, I ran into an error: {str(e)}")
    finally:
        active_imagine_requests.discard(chat_id)