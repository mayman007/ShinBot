import os
import logging.config
from telethon import TelegramClient
from utils.command_registry import register_handlers
from utils.logger import LOGGING_CONFIG
from config import BOT_TOKEN, API_ID, API_HASH
from handlers import check_pending_timers

async def startup(client):
    await check_pending_timers(client)

def main():
    # Create necessary directories
    os.makedirs('db', exist_ok=True)
    os.makedirs('downloads', exist_ok=True)

    # Initialize logger
    logging.config.dictConfig(LOGGING_CONFIG)

    # Initialize Telethon client for a bot.
    client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

    # Register command handlers
    register_handlers(client)

    print("Bot is running...")
    client.loop.create_task(startup(client))
    client.run_until_disconnected()

if __name__ == '__main__':
    main()
