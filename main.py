import os
import logging.config
from telethon import TelegramClient, events
from utils.logger import LOGGING_CONFIG
from config import BOT_TOKEN, API_ID, API_HASH, ENABLE_GEMINI_COMMAND, ENABLE_IMAGINE_COMMAND, ENABLE_MEME_COMMAND
import handlers.command_handlers as command_handlers
import handlers.message_handlers as messages_event_handlers
import handlers.callback_handlers as callback_handlers
import handlers.yt_handlers as yt_handlers
from utils.timer_scheduler import check_pending_timers

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
    client.add_event_handler(command_handlers.start_command, events.NewMessage(pattern=r'^/start'))
    client.add_event_handler(command_handlers.help_command, events.NewMessage(pattern=r'^/help'))
    client.add_event_handler(command_handlers.list_join_dates, events.NewMessage(pattern=r'^/joindate'))
    client.add_event_handler(command_handlers.usagedata_command, events.NewMessage(pattern=r'^/usagedata'))
    client.add_event_handler(command_handlers.character_command, events.NewMessage(pattern=r'^/character'))
    client.add_event_handler(command_handlers.anime_command, events.NewMessage(pattern=r'^/anime'))
    client.add_event_handler(command_handlers.manga_command, events.NewMessage(pattern=r'^/manga'))
    client.add_event_handler(command_handlers.aghpb_command, events.NewMessage(pattern=r'^/aghpb'))
    client.add_event_handler(command_handlers.echo_command, events.NewMessage(pattern=r'^/echo'))
    client.add_event_handler(command_handlers.ping_command, events.NewMessage(pattern=r'^/ping'))
    client.add_event_handler(command_handlers.timer_command, events.NewMessage(pattern=r'^/timer(@\w+)?(\s|$)'))
    client.add_event_handler(command_handlers.list_timers_command, events.NewMessage(pattern=r'^/timerslist(@\w+)?'))
    client.add_event_handler(command_handlers.remove_timer_command, events.NewMessage(pattern=r'^/timerdel(@\w+)?(\s|$)'))
    client.add_event_handler(command_handlers.reverse_command, events.NewMessage(pattern=r'^/reverse'))
    client.add_event_handler(command_handlers.slot_command, events.NewMessage(pattern=r'^/slot'))
    client.add_event_handler(command_handlers.coinflip_command, events.NewMessage(pattern=r'^/coinflip'))
    if ENABLE_MEME_COMMAND:
        client.add_event_handler(command_handlers.meme_command, events.NewMessage(pattern=r'^/meme'))
    client.add_event_handler(command_handlers.geekjoke_command, events.NewMessage(pattern=r'^/geekjoke'))
    client.add_event_handler(command_handlers.dadjoke_command, events.NewMessage(pattern=r'^/dadjoke'))
    client.add_event_handler(command_handlers.dog_command, events.NewMessage(pattern=r'^/dog'))
    client.add_event_handler(command_handlers.affirmation_command, events.NewMessage(pattern=r'^/affirmation'))
    client.add_event_handler(command_handlers.advice_command, events.NewMessage(pattern=r'^/advice'))
    if ENABLE_GEMINI_COMMAND:
        client.add_event_handler(command_handlers.gemini_command, events.NewMessage(pattern=r'^/gemini'))
    if ENABLE_IMAGINE_COMMAND:
        client.add_event_handler(command_handlers.imagine_command, events.NewMessage(pattern=r'^/imagine'))

    # YouTube command handlers
    client.add_event_handler(yt_handlers.yt_command, events.NewMessage(pattern=r'^/yt'))
    client.add_event_handler(yt_handlers.yt_quality_button, events.CallbackQuery(pattern=r"^yt_\d+"))
    client.add_event_handler(yt_handlers.yt_audio_button, events.CallbackQuery(pattern=r'^yt_audio_\d+'))
    client.add_event_handler(yt_handlers.yt_subs_callback, events.CallbackQuery(pattern=r'^subs_'))

    # Register a handler for text messages that are not commands
    client.add_event_handler(
        messages_event_handlers.message_event,
        events.NewMessage(func=lambda e: not e.raw_text.startswith('/'))
    )

    # Register a callback query handler for button clicks
    client.add_event_handler(callback_handlers.button_click_handler, events.CallbackQuery())

    print("Bot is running...")
    client.loop.create_task(startup(client))
    client.run_until_disconnected()

if __name__ == '__main__':
    main()
