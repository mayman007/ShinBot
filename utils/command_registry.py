from telethon import events
from config import ENABLE_GEMINI_COMMAND, ENABLE_IMAGINE_COMMAND, ENABLE_MEME_COMMAND
import handlers as handlers


# Register command handlers
def register_handlers(client):

    client.add_event_handler(handlers.start_command, events.NewMessage(pattern=r'(?i)^/start'))
    client.add_event_handler(handlers.help_command, events.NewMessage(pattern=r'(?i)^/help'))
    client.add_event_handler(handlers.mute_command, events.NewMessage(pattern=r'(?i)^/mute'))
    client.add_event_handler(handlers.unmute_command, events.NewMessage(pattern=r'(?i)^/unmute'))
    client.add_event_handler(handlers.list_join_dates, events.NewMessage(pattern=r'(?i)^/joindate'))
    client.add_event_handler(handlers.usagedata_command, events.NewMessage(pattern=r'(?i)^/usagedata'))
    client.add_event_handler(handlers.character_command, events.NewMessage(pattern=r'(?i)^/character'))
    client.add_event_handler(handlers.anime_command, events.NewMessage(pattern=r'(?i)^/anime'))
    client.add_event_handler(handlers.manga_command, events.NewMessage(pattern=r'(?i)^/manga'))
    client.add_event_handler(handlers.aghpb_command, events.NewMessage(pattern=r'(?i)^/aghpb'))
    client.add_event_handler(handlers.echo_command, events.NewMessage(pattern=r'(?i)^/echo'))
    client.add_event_handler(handlers.ping_command, events.NewMessage(pattern=r'(?i)^/ping'))
    client.add_event_handler(handlers.timer_command, events.NewMessage(pattern=r'(?i)^/timer(@\w+)?(\s|$)'))
    client.add_event_handler(handlers.list_timers_command, events.NewMessage(pattern=r'(?i)^/timerslist(@\w+)?'))
    client.add_event_handler(handlers.remove_timer_command, events.NewMessage(pattern=r'(?i)^/timerdel(@\w+)?(\s|$)'))
    client.add_event_handler(handlers.reverse_command, events.NewMessage(pattern=r'(?i)^/reverse'))
    client.add_event_handler(handlers.slot_command, events.NewMessage(pattern=r'(?i)^/slot'))
    client.add_event_handler(handlers.coinflip_command, events.NewMessage(pattern=r'(?i)^/coinflip'))
    if ENABLE_MEME_COMMAND:
        client.add_event_handler(handlers.meme_command, events.NewMessage(pattern=r'(?i)^/meme'))
    client.add_event_handler(handlers.geekjoke_command, events.NewMessage(pattern=r'(?i)^/geekjoke'))
    client.add_event_handler(handlers.dadjoke_command, events.NewMessage(pattern=r'(?i)^/dadjoke'))
    client.add_event_handler(handlers.dog_command, events.NewMessage(pattern=r'(?i)^/dog'))
    client.add_event_handler(handlers.affirmation_command, events.NewMessage(pattern=r'(?i)^/affirmation'))
    client.add_event_handler(handlers.advice_command, events.NewMessage(pattern=r'(?i)^/advice'))
    if ENABLE_GEMINI_COMMAND:
        client.add_event_handler(handlers.gemini_command, events.NewMessage(pattern=r'(?i)^/gemini'))
    if ENABLE_IMAGINE_COMMAND:
        client.add_event_handler(handlers.imagine_command, events.NewMessage(pattern=r'(?i)^/imagine'))

    # YouTube command handlers
    handlers.register_yt_handlers(client)  # Use the proper registration function

    # Register a handler for text messages that are not commands
    client.add_event_handler(
        handlers.message_event,
        events.NewMessage(func=lambda e: not e.raw_text.startswith('/'))
    )

    # Register a callback query handler for button clicks
    client.add_event_handler(handlers.button_click_handler, events.CallbackQuery())
