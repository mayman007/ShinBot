import aiohttp
import aiosqlite
import ast
from pyrogram import Client, types
from pyrogram.types import InlineKeyboardButton, InputMediaPhoto, InlineKeyboardMarkup
from pyrogram.errors import FloodWait
from config import BOT_USERNAME
from utils.usage import save_usage


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


async def handle_manga_callback(client: Client, callback_query):
    """Handle manga pagination callbacks."""
    data = callback_query.data
    
    async with aiosqlite.connect("db/database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM manga WHERE message_id = ?", (str(callback_query.message.id),)
            )
            db_data = await cursor.fetchall()

    if not db_data:
        await callback_query.answer("No data found.")
        return

    current_index = db_data[0][1]
    manga_results_list = ast.literal_eval(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
    btn_type = "prev" if "prev" in data else "next" if "next" in data else None
    
    if current_index == 0 and btn_type == "prev":
        await callback_query.answer()
        return
    if current_index == len(manga_results_list) - 1 and btn_type == "next":
        await callback_query.answer()
        return

    if current_index == 0:
        prev_index = 0
        next_index = 1
    elif current_index == len(manga_results_list) - 1:
        prev_index = current_index - 1
        next_index = current_index
    else:
        prev_index = current_index - 1
        next_index = current_index + 1

    updated_index = prev_index if btn_type == "prev" else next_index if btn_type == "next" else current_index
    if updated_index == current_index:
        await callback_query.answer()
        return

    image_link = manga_results_list[updated_index]['image_url']
    message_content = (
        f"__**{updated_index + 1}/{len(manga_results_list)}**__\n"
        f"**🎗️ Title:** {manga_results_list[updated_index]['title']}\n"
        f"**👓 Type:** {manga_results_list[updated_index]['the_type']}\n"
        f"**⭐ Score:** {manga_results_list[updated_index]['score']}\n"
        f"**📃 Chapters:** {manga_results_list[updated_index]['chapters']}\n"
        f"**📅 Year:** {manga_results_list[updated_index]['year']}\n"
        f"**🎆 Themes:** {manga_results_list[updated_index]['themes']}\n"
        f"**🎞️ Genres:** {manga_results_list[updated_index]['genres']}"
    )
    
    buttons = [
        [
            InlineKeyboardButton("Previous", callback_data="mangaprev"),
            InlineKeyboardButton("Next", callback_data="manganext")
        ],
        [
            InlineKeyboardButton("Open in MAL", url=manga_results_list[updated_index]['url'])
        ]
    ]

    # Edit the message with new content and buttons
    try:
        await callback_query.message.edit_media(
            media=InputMediaPhoto(media=image_link, caption=message_content),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except FloodWait as e:
        await callback_query.answer(f"Please wait {e.value} seconds before trying again.", show_alert=True)
        return
    except Exception as e:
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)
        return
        
    await callback_query.answer()

    async with aiosqlite.connect("db/database.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "UPDATE manga SET current_index = ? WHERE message_id = ?",
                (updated_index, str(callback_query.message.id))
            )
            await connection.commit()
