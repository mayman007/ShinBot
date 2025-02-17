import logging.config
from utils.logger import logger, LOGGING_CONFIG, DEBUG
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN, ENABLE_GEMINI_COMMAND, ENABLE_IMAGINE_COMMAND, ENABLE_MEME_COMMAND
import handlers.command_handlers as command_handlers
import handlers.message_handlers as messages_event_handlers
import handlers.callback_handlers as callback_handlers


def main():
    # Create db directory
    os.makedirs('db', exist_ok=True)

    # Initialize logger
    logging.config.dictConfig(LOGGING_CONFIG)

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