import logging
import os
import aiosqlite
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN, DEBUG, ENABLE_GEMINI_COMMAND, ENABLE_IMAGINE_COMMAND, ENABLE_MEME_COMMAND
import handlers.command_handlers as command_handlers
import handlers.message_handlers as messages_event_handlers
import handlers.callback_handlers as callback_handlers

# Save Commands Usage in Database
async def save_usage(chat_object, command_name: str):
    if chat_object.type in ['group', 'supergroup']:
        chat_id = str(chat_object.id)
        chat_name = str(chat_object.title)
        chat_type = str(chat_object.type)
        # chat_members = str(chat_object.get_member_count())
        # chat_invite = str(chat_object.invite_link if chat_object.invite_link else "_")
        chat_members = "idk"
        chat_invite = "idk"
    elif chat_object.type in ['private', 'bot']:
        chat_id = str(chat_object.id)
        chat_name = str(chat_object.username if chat_object.username else chat_object.first_name)
        chat_type = str(chat_object.type)
        chat_members = str("_")
        chat_invite = str("_")
        
    async with aiosqlite.connect("db/usage.db") as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(f"CREATE TABLE IF NOT EXISTS {command_name} (id TEXT, name TEXT, usage INTEGER, type TEXT, members TEXT, invite TEXT)")
            cursor = await cursor.execute(f"SELECT * FROM {command_name} WHERE id = ?", (chat_id,))
            row = await cursor.fetchone()
            if row == None:
                await cursor.execute(f"INSERT INTO {command_name} (id, name, usage, type, members, invite) VALUES (?, ?, ?, ?, ?, ?)", (chat_id, chat_name, 1, chat_type, chat_members, chat_invite,))
            else:
                await cursor.execute(f"UPDATE {command_name} SET usage = ? WHERE id = ?", (row[2] + 1, chat_id))
            await connection.commit()


# Set up logging to help with debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if DEBUG else logging.WARNING
)
logger = logging.getLogger(__name__)

def main():
    # Create downloads directory
    os.makedirs('db', exist_ok=True)
    # Initialize bot with token from config
    application = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", command_handlers.start_command))
    application.add_handler(CommandHandler("help", command_handlers.help_command))
    application.add_handler(CommandHandler("usagedata", command_handlers.usagedata_command))
    application.add_handler(CommandHandler("character", command_handlers.character_command))
    application.add_handler(CommandHandler("anime", command_handlers.anime_command))
    application.add_handler(CommandHandler("manga", command_handlers.manga_command))
    application.add_handler(CommandHandler("aghpb", command_handlers.aghpb_command))
    application.add_handler(CommandHandler("echo", command_handlers.echo_command))
    application.add_handler(CommandHandler("ping", command_handlers.ping_command))
    application.add_handler(CommandHandler("timer", command_handlers.timer_command))
    application.add_handler(CommandHandler("reverse", command_handlers.reverse_command))
    application.add_handler(CommandHandler("slot", command_handlers.slot_command))
    application.add_handler(CommandHandler("coinflip", command_handlers.coinflip_command))
    if ENABLE_MEME_COMMAND: application.add_handler(CommandHandler("meme", command_handlers.meme_command))
    application.add_handler(CommandHandler("geekjoke", command_handlers.geekjoke_command))
    application.add_handler(CommandHandler("dadjoke", command_handlers.dadjoke_command))
    application.add_handler(CommandHandler("dog", command_handlers.dog_command))
    application.add_handler(CommandHandler("affirmation", command_handlers.affirmation_command))
    application.add_handler(CommandHandler("advice", command_handlers.advice_command))
    if ENABLE_GEMINI_COMMAND: application.add_handler(CommandHandler("gemini", command_handlers.gemini_command))
    if ENABLE_IMAGINE_COMMAND: application.add_handler(CommandHandler("imagine", command_handlers.imagine_command))

    # Add messages events handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages_event_handlers.message_event))

    # Add buttons handlers
    application.add_handler(CallbackQueryHandler(callback_handlers.button_click_handler))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()