from telethon import events
from config import ENABLE_GEMINI_COMMAND, ENABLE_IMAGINE_COMMAND, ENABLE_MEME_COMMAND
import handlers as handlers


# Register command handlers
def register_handlers(client):

    client.add_event_handler(handlers.start_command, events.NewMessage(pattern=r'^/start'))
    client.add_event_handler(handlers.help_command, events.NewMessage(pattern=r'^/help'))
    client.add_event_handler(handlers.list_join_dates, events.NewMessage(pattern=r'^/joindate'))
    client.add_event_handler(handlers.usagedata_command, events.NewMessage(pattern=r'^/usagedata'))
    client.add_event_handler(handlers.character_command, events.NewMessage(pattern=r'^/character'))
    client.add_event_handler(handlers.anime_command, events.NewMessage(pattern=r'^/anime'))
    client.add_event_handler(handlers.manga_command, events.NewMessage(pattern=r'^/manga'))
    client.add_event_handler(handlers.aghpb_command, events.NewMessage(pattern=r'^/aghpb'))
    client.add_event_handler(handlers.echo_command, events.NewMessage(pattern=r'^/echo'))
    client.add_event_handler(handlers.ping_command, events.NewMessage(pattern=r'^/ping'))
    client.add_event_handler(handlers.timer_command, events.NewMessage(pattern=r'^/timer(@\w+)?(\s|$)'))
    client.add_event_handler(handlers.list_timers_command, events.NewMessage(pattern=r'^/timerslist(@\w+)?'))
    client.add_event_handler(handlers.remove_timer_command, events.NewMessage(pattern=r'^/timerdel(@\w+)?(\s|$)'))
    client.add_event_handler(handlers.reverse_command, events.NewMessage(pattern=r'^/reverse'))
    client.add_event_handler(handlers.slot_command, events.NewMessage(pattern=r'^/slot'))
    client.add_event_handler(handlers.coinflip_command, events.NewMessage(pattern=r'^/coinflip'))
    client.add_event_handler(handlers.choose_command, events.NewMessage(pattern=r'^/choose'))
    if ENABLE_MEME_COMMAND:
        client.add_event_handler(handlers.meme_command, events.NewMessage(pattern=r'^/meme'))
        client.add_event_handler(handlers.meme_command, events.NewMessage(pattern=r'^/meme'))
    client.add_event_handler(handlers.geekjoke_command, events.NewMessage(pattern=r'^/geekjoke'))
    client.add_event_handler(handlers.dadjoke_command, events.NewMessage(pattern=r'^/dadjoke'))
    client.add_event_handler(handlers.dog_command, events.NewMessage(pattern=r'^/dog'))
    client.add_event_handler(handlers.affirmation_command, events.NewMessage(pattern=r'^/affirmation'))
    client.add_event_handler(handlers.advice_command, events.NewMessage(pattern=r'^/advice'))
    if ENABLE_GEMINI_COMMAND:
        client.add_event_handler(handlers.gemini_command, events.NewMessage(pattern=r'^/gemini'))
    if ENABLE_IMAGINE_COMMAND:
        client.add_event_handler(handlers.imagine_command, events.NewMessage(pattern=r'^/imagine'))

    # YouTube command handlers
    handlers.register_yt_handlers(client)  # Use the proper registration function

    # Register a handler for text messages that are not commands
    client.add_event_handler(
        handlers.message_event,
        events.NewMessage(func=lambda e: not e.raw_text.startswith('/'))
    )

    # Register a callback query handler for button clicks
    client.add_event_handler(handlers.button_click_handler, events.CallbackQuery())
