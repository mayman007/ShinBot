import aiosqlite
import ast
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes


# ---------- Callback Query Handler for Pagination ----------
async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("anime"):
        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM anime WHERE message_id = ?", (str(query.message.message_id),)
                )
                db_data = await cursor.fetchall()

        if not db_data:
            await query.answer("No data found.")
            return

        current_index = db_data[0][1]
        anime_results_list = ast.literal_eval(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
        btn_type = "prev" if "prev" in data else "next" if "next" in data else None
        if current_index == 0:
            prev_index = 0
            next_index = 1
        elif current_index == 4:
            prev_index = 3
            next_index = 4
        else:
            prev_index = current_index - 1
            next_index = current_index + 1

        updated_index = prev_index if btn_type == "prev" else next_index if btn_type == "next" else current_index
        if updated_index == current_index:
            await query.answer()
            return

        image_link = anime_results_list[updated_index]['image_url']
        message_content = (
            f"__**{updated_index + 1}**__\n"
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

        if anime_results_list[updated_index]['trailer'] in (None, "None"):
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Previous", callback_data="animeprev"),
                    InlineKeyboardButton("Next", callback_data="animenext")
                ],
                [
                    InlineKeyboardButton("Open in MAL", url=anime_results_list[updated_index]['url'])
                ]
            ])
        else:
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Previous", callback_data="animeprev"),
                    InlineKeyboardButton("Next", callback_data="animenext")
                ],
                [
                    InlineKeyboardButton("Open in MAL", url=anime_results_list[updated_index]['url'])
                ],
                [
                    InlineKeyboardButton("Watch Trailer", url=anime_results_list[updated_index]['trailer'])
                ]
            ])

        await query.message.edit_media(
            media=InputMediaPhoto(media=image_link, caption=message_content)
        )
        await query.message.edit_reply_markup(reply_markup=buttons)
        await query.answer()

        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "UPDATE anime SET current_index = ? WHERE message_id = ?",
                    (updated_index, str(query.message.message_id))
                )
                await connection.commit()

    elif data.startswith("manga"):
        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "SELECT * FROM manga WHERE message_id = ?", (str(query.message.message_id),)
                )
                db_data = await cursor.fetchall()

        if not db_data:
            await query.answer("No data found.")
            return

        current_index = db_data[0][1]
        manga_results_list = ast.literal_eval(db_data[0][2].replace("'", "\"").replace("None", "\"None\""))
        btn_type = "prev" if "prev" in data else "next" if "next" in data else None
        if current_index == 0:
            prev_index = 0
            next_index = 1
        elif current_index == 4:
            prev_index = 3
            next_index = 4
        else:
            prev_index = current_index - 1
            next_index = current_index + 1

        updated_index = prev_index if btn_type == "prev" else next_index if btn_type == "next" else current_index
        if updated_index == current_index:
            await query.answer()
            return

        image_link = manga_results_list[updated_index]['image_url']
        message_content = (
            f"__**{updated_index + 1}**__\n"
            f"**🎗️ Title:** {manga_results_list[updated_index]['title']}\n"
            f"**👓 Type:** {manga_results_list[updated_index]['the_type']}\n"
            f"**⭐ Score:** {manga_results_list[updated_index]['score']}\n"
            f"**📃 Chapters:** {manga_results_list[updated_index]['chapters']}\n"
            f"**📅 Year:** {manga_results_list[updated_index]['year']}\n"
            f"**🎆 Themes:** {manga_results_list[updated_index]['themes']}\n"
            f"**🎞️ Genres:** {manga_results_list[updated_index]['genres']}"
        )
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Previous", callback_data="mangaprev"),
                InlineKeyboardButton("Next", callback_data="manganext")
            ],
            [
                InlineKeyboardButton("Open in MAL", url=manga_results_list[updated_index]['url'])
            ]
        ])

        await query.message.edit_media(
            media=InputMediaPhoto(media=image_link, caption=message_content)
        )
        await query.message.edit_reply_markup(reply_markup=buttons)
        await query.answer()

        async with aiosqlite.connect("db/database.db") as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(
                    "UPDATE manga SET current_index = ? WHERE message_id = ?",
                    (updated_index, str(query.message.message_id))
                )
                await connection.commit()