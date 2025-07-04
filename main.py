import os
import logging.config
import asyncio
from pyrogram import Client
from utils.command_registry import register_handlers
from utils.logger import LOGGING_CONFIG
from config import BOT_TOKEN, API_ID, API_HASH
from handlers import check_pending_timers
from handlers.moderation.warn_system import init_warns_db

async def startup(client: Client):
    await check_pending_timers(client)
    await init_warns_db()
    # Get bot info for debugging
    me = await client.get_me()
    logger = logging.getLogger(__name__)
    logger.info(f"Bot started: @{me.username} (ID: {me.id})")
    
    # Test admin checking in a debug mode
    logger.info("Bot initialization complete - admin checking should work now")

async def main():
    # Create necessary directories
    os.makedirs('db', exist_ok=True)
    os.makedirs('downloads', exist_ok=True)

    # Initialize logger
    logging.config.dictConfig(LOGGING_CONFIG)

    # Initialize Pyrogram client for a bot.
    client = Client('bot_session', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

    # Register command handlers
    register_handlers(client)

    async with client:
        print("Bot is running...")
        await startup(client)
        # Keep the bot running
        await asyncio.Future()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
