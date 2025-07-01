from telethon import events
from config import ENABLE_GEMINI_COMMAND, ENABLE_IMAGINE_COMMAND, ENABLE_MEME_COMMAND, BOT_USERNAME
import handlers as handlers


# Register command handlers
def register_handlers(client):
    # Create pattern suffix to match only our bot or no bot mention
    bot_pattern = f"(@{BOT_USERNAME})?(?:\\s|$)"

    client.add_event_handler(handlers.start_command, events.NewMessage(pattern=f'(?i)^/start{bot_pattern}'))
    client.add_event_handler(handlers.help_command, events.NewMessage(pattern=f'(?i)^/help{bot_pattern}'))
    client.add_event_handler(handlers.mute_command, events.NewMessage(pattern=f'(?i)^/mute{bot_pattern}'))
    client.add_event_handler(handlers.unmute_command, events.NewMessage(pattern=f'(?i)^/unmute{bot_pattern}'))
    client.add_event_handler(handlers.list_join_dates, events.NewMessage(pattern=f'(?i)^/joindate{bot_pattern}'))
    client.add_event_handler(handlers.usagedata_command, events.NewMessage(pattern=f'(?i)^/usagedata{bot_pattern}'))
    client.add_event_handler(handlers.character_command, events.NewMessage(pattern=f'(?i)^/character{bot_pattern}'))
    client.add_event_handler(handlers.anime_command, events.NewMessage(pattern=f'(?i)^/anime{bot_pattern}'))
    client.add_event_handler(handlers.manga_command, events.NewMessage(pattern=f'(?i)^/manga{bot_pattern}'))
    client.add_event_handler(handlers.aghpb_command, events.NewMessage(pattern=f'(?i)^/aghpb{bot_pattern}'))
    client.add_event_handler(handlers.echo_command, events.NewMessage(pattern=f'(?i)^/echo{bot_pattern}'))
    client.add_event_handler(handlers.ping_command, events.NewMessage(pattern=f'(?i)^/ping{bot_pattern}'))
    client.add_event_handler(handlers.timer_command, events.NewMessage(pattern=r'(?i)^/timer(@\w+)?(\s|$)'))
    client.add_event_handler(handlers.list_timers_command, events.NewMessage(pattern=r'(?i)^/timerslist(@\w+)?'))
    client.add_event_handler(handlers.remove_timer_command, events.NewMessage(pattern=r'(?i)^/timerdel(@\w+)?(\s|$)'))
    client.add_event_handler(handlers.reverse_command, events.NewMessage(pattern=f'(?i)^/reverse{bot_pattern}'))
    client.add_event_handler(handlers.slot_command, events.NewMessage(pattern=f'(?i)^/slot{bot_pattern}'))
    client.add_event_handler(handlers.coinflip_command, events.NewMessage(pattern=f'(?i)^/coinflip{bot_pattern}'))
    if ENABLE_MEME_COMMAND:
        client.add_event_handler(handlers.meme_command, events.NewMessage(pattern=f'(?i)^/meme{bot_pattern}'))
    client.add_event_handler(handlers.geekjoke_command, events.NewMessage(pattern=f'(?i)^/geekjoke{bot_pattern}'))
    client.add_event_handler(handlers.dadjoke_command, events.NewMessage(pattern=f'(?i)^/dadjoke{bot_pattern}'))
    client.add_event_handler(handlers.dog_command, events.NewMessage(pattern=f'(?i)^/dog{bot_pattern}'))
    client.add_event_handler(handlers.affirmation_command, events.NewMessage(pattern=f'(?i)^/affirmation{bot_pattern}'))
    client.add_event_handler(handlers.advice_command, events.NewMessage(pattern=f'(?i)^/advice{bot_pattern}'))
    if ENABLE_GEMINI_COMMAND:
        client.add_event_handler(handlers.gemini_command, events.NewMessage(pattern=f'(?i)^/gemini{bot_pattern}'))
    if ENABLE_IMAGINE_COMMAND:
        client.add_event_handler(handlers.imagine_command, events.NewMessage(pattern=f'(?i)^/imagine{bot_pattern}'))

    # YouTube command handlers
    handlers.register_yt_handlers(client)  # Use the proper registration function

    # Register a handler for text messages that are not commands
    client.add_event_handler(
        handlers.message_event,
        events.NewMessage(func=lambda e: not e.raw_text.startswith('/'))
    )

    # Register a callback query handler for button clicks
    client.add_event_handler(handlers.button_click_handler, events.CallbackQuery())
