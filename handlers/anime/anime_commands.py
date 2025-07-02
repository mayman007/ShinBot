import io
import aiohttp
import aiosqlite
from pyrogram import Client, types
from config import BOT_USERNAME
from utils.usage import save_usage


# ---------------------------
# Anime Command Handler
# ---------------------------
async def anime_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "anime")
    
    text = message.text
    query = text.replace("/anime", "").replace(f"@{BOT_USERNAME}", "").strip()
    if not query:
        await message.reply("Please provide a search query.")
        return

    index = 0
    anime_results_list = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.jikan.moe/v4/anime?q={query}&order_by=favorites&sort=desc&sfw=true") as response:
                if response.status == 200:
                    results = await response.json()
                else:
                    await message.reply(f"API Error: Status {response.status}")
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
        await message.reply(f"Error fetching data: {str(e)}")
        return

    if index == 0:
        await message.reply("No results found.")
        return

    try:
        buttons = []
        if anime_results_list[0]['trailer'] is None:
            buttons = [
                [types.InlineKeyboardButton("Previous", callback_data="animeprev"), types.InlineKeyboardButton("Next", callback_data="animenext")],
                [types.InlineKeyboardButton("Open in MAL", url=anime_results_list[0]['url'])]
            ]
        else:
            buttons = [
                [types.InlineKeyboardButton("Previous", callback_data="animeprev"), types.InlineKeyboardButton("Next", callback_data="animenext")],
                [types.InlineKeyboardButton("Open in MAL", url=anime_results_list[0]['url'])],
                [types.InlineKeyboardButton("Watch Trailer", url=anime_results_list[0]['trailer'])]
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
        sent_msg = await client.send_photo(
            chat.id,
            anime_results_list[0]['image_url'],
            caption=caption,
            reply_markup=types.InlineKeyboardMarkup(buttons)
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
        await message.reply(f"Error displaying results: {str(e)}")

# ---------------------------
# Manga Command Handler
# ---------------------------
async def manga_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "manga")
    
    text = message.text
    query = text.replace("/manga", "").replace(f"@{BOT_USERNAME}", "").strip()
    if not query:
        await message.reply("Please provide a search query.")
        return
    
    index = 0
    manga_results_list = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.jikan.moe/v4/manga?q={query}&order_by=favorites&sort=desc&sfw=true") as response:
                if response.status == 200:
                    results = await response.json()
                else:
                    await message.reply(f"API Error: Status {response.status}")
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
        await message.reply(f"Error fetching data: {str(e)}")
        return

    if index == 0:
        await message.reply("No results found.")
        return

    try:
        buttons = [
            [types.InlineKeyboardButton("Previous", callback_data="mangaprev"), types.InlineKeyboardButton("Next", callback_data="manganext")],
            [types.InlineKeyboardButton("Open in MAL", url=manga_results_list[0]['url'])]
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
        sent_msg = await client.send_photo(
            chat.id,
            manga_results_list[0]['image_url'],
            caption=caption,
            reply_markup=types.InlineKeyboardMarkup(buttons)
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
        await message.reply(f"Error displaying results: {str(e)}")

# ---------------------------
# Character Command Handler
# ---------------------------
async def character_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "character")
    
    # Remove command from text and get query
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Please provide a search query.")
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
                    await message.reply(f"API Error: Status {response.status}")
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
            await message.reply(f"Error fetching data: {str(e)}")
            return

    if index == 0:
        await message.reply("No results found.")
        return

    try:
        buttons = [[types.InlineKeyboardButton("Open in MAL", url=character_results_list[0]['url'])]]
        msg = await client.send_photo(
            chat.id,
            character_results_list[0]['image_url'],
            caption=(
                f"**🎗️ Name:** {character_results_list[0]['name']}\n"
                f"**⭐ Favorites:** {character_results_list[0]['favorites']}\n"
                f"**👓 About:** {character_results_list[0]['about']}"
            ),
            reply_markup=types.InlineKeyboardMarkup(buttons)
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
        await message.reply(f"Error displaying results: {str(e)}")

# ---------------------------
# AGHPB Command Handler
# ---------------------------
async def aghpb_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "aghpb")
    
    url = "https://api.devgoldy.xyz/aghpb/v1/random"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_bytes = await response.read()
                    image_file = io.BytesIO(image_bytes)
                    image_file.name = "aghpb.jpg"  # Add a filename
                    await message.reply_photo(photo=image_file)
                else:
                    await message.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await message.reply(f"Error fetching image: {str(e)}")