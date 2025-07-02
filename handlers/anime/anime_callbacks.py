from pyrogram.types import InlineKeyboardButton, InputMediaPhoto, InlineKeyboardMarkup
from pyrogram import Client
from pyrogram.errors import FloodWait
import aiosqlite
import ast

# ---------- Callback Query Handler for Pagination ----------
async def button_click_handler(client: Client, callback_query):
    data = callback_query.data
    
    if data.startswith("anime"):
        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM anime WHERE message_id = ?", (str(callback_query.message.id),)
                )
                db_data = await cursor.fetchall()

        if not db_data:
            await callback_query.answer("No data found.")
            return

        current_index = db_data[0][1]
        anime_results_list = ast.literal_eval(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
        btn_type = "prev" if "prev" in data else "next" if "next" in data else None
        
        if current_index == 0 and btn_type == "prev":
            await callback_query.answer()
            return
        if current_index == len(anime_results_list) - 1 and btn_type == "next":
            await callback_query.answer()
            return

        if current_index == 0:
            prev_index = 0
            next_index = 1
        elif current_index == len(anime_results_list) - 1:
            prev_index = current_index - 1
            next_index = current_index
        else:
            prev_index = current_index - 1
            next_index = current_index + 1

        updated_index = prev_index if btn_type == "prev" else next_index if btn_type == "next" else current_index
        if updated_index == current_index:
            await callback_query.answer()
            return

        image_link = anime_results_list[updated_index]['image_url']
        message_content = (
            f"__**{updated_index + 1}/{len(anime_results_list)}**__\n"
            f"**🎗️ Title:** {anime_results_list[updated_index]['title']}\n"
            f"**👓 Type:** {anime_results_list[updated_index]['the_type']}\n"
            f"**⭐ Score:** {anime_results_list[updated_index]['score']}\n"
            f"**📃 Episodes:** {anime_results_list[updated_index]['episodes']}\n"
            f"**📅 Year:** {anime_results_list[updated_index]['year']}\n"
            f"**🎆 Themes:** {anime_results_list[updated_index]['themes']}\n"
            f"**🎞️ Genres:** {anime_results_list[updated_index]['genres']}\n"
            f"**🏢 Studio:** {anime_results_list[updated_index]['studios']}\n"
            f"**🧬 Source:** {anime_results_list[updated_index]['source']}"
        )

        buttons = []
        # Navigation buttons
        buttons.append([
            InlineKeyboardButton("Previous", callback_data="animeprev"),
            InlineKeyboardButton("Next", callback_data="animenext")
        ])
        # MAL button
        buttons.append([
            InlineKeyboardButton("Open in MAL", url=anime_results_list[updated_index]['url'])
        ])
        # Trailer button (if available)
        if anime_results_list[updated_index]['trailer'] not in (None, "None"):
            buttons.append([
                InlineKeyboardButton("Watch Trailer", url=anime_results_list[updated_index]['trailer'])
            ])

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
                    "UPDATE anime SET current_index = ? WHERE message_id = ?",
                    (updated_index, str(callback_query.message.id))
                )
                await connection.commit()

    elif data.startswith("manga"):
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