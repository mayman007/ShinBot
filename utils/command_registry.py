from pyrogram import filters, Client
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from config import ENABLE_GEMINI_COMMAND, ENABLE_IMAGINE_COMMAND, ENABLE_MEME_COMMAND
import handlers as handlers


# Register command handlers
def register_handlers(client: Client):
    # Pyrogram's command filter handles the bot username suffix automatically.
    client.add_handler(MessageHandler(handlers.start_command, filters.command("start")))
    client.add_handler(MessageHandler(handlers.help_command, filters.command("help")))
    client.add_handler(MessageHandler(handlers.mute_command, filters.command("mute") & filters.group))
    client.add_handler(MessageHandler(handlers.unmute_command, filters.command("unmute") & filters.group))
    client.add_handler(MessageHandler(handlers.list_join_dates, filters.command("joindate")))
    client.add_handler(MessageHandler(handlers.usagedata_command, filters.command("usagedata")))
    client.add_handler(MessageHandler(handlers.character_command, filters.command("character")))
    client.add_handler(MessageHandler(handlers.anime_command, filters.command("anime")))
    client.add_handler(MessageHandler(handlers.manga_command, filters.command("manga")))
    client.add_handler(MessageHandler(handlers.aghpb_command, filters.command("aghpb")))
    client.add_handler(MessageHandler(handlers.echo_command, filters.command("echo")))
    client.add_handler(MessageHandler(handlers.ping_command, filters.command("ping")))
    client.add_handler(MessageHandler(handlers.chatid_command, filters.command("chatid")))
    client.add_handler(MessageHandler(handlers.pfp_command, filters.command("pfp")))
    client.add_handler(MessageHandler(handlers.calc_command, filters.command("calc")))
    client.add_handler(MessageHandler(handlers.groupinfo_command, filters.command("groupinfo")))
    client.add_handler(MessageHandler(handlers.timer_command, filters.command("timer")))
    client.add_handler(MessageHandler(handlers.list_timers_command, filters.command("timerslist")))
    client.add_handler(MessageHandler(handlers.remove_timer_command, filters.command("timerdel")))
    client.add_handler(MessageHandler(handlers.reverse_command, filters.command("reverse")))
    client.add_handler(MessageHandler(handlers.slot_command, filters.command("slot")))
    client.add_handler(MessageHandler(handlers.coinflip_command, filters.command("coinflip")))
    client.add_handler(MessageHandler(handlers.choose_command, filters.command("choose")))
    client.add_handler(MessageHandler(handlers.rps_command, filters.command("rps")))
    client.add_handler(MessageHandler(handlers.geekjoke_command, filters.command("geekjoke")))
    client.add_handler(MessageHandler(handlers.dadjoke_command, filters.command("dadjoke")))
    client.add_handler(MessageHandler(handlers.dog_command, filters.command("dog")))
    client.add_handler(MessageHandler(handlers.affirmation_command, filters.command("affirmation")))
    client.add_handler(MessageHandler(handlers.advice_command, filters.command("advice")))
    client.add_handler(MessageHandler(handlers.warn_command, filters.command("warn")))
    client.add_handler(MessageHandler(handlers.warndel_command, filters.command("warndel")))
    client.add_handler(MessageHandler(handlers.warnsuser_command, filters.command("warnsuser")))
    client.add_handler(MessageHandler(handlers.warnslist_command, filters.command("warnslist")))
    client.add_handler(MessageHandler(handlers.ban_user, filters.command("ban")))
    client.add_handler(MessageHandler(handlers.unban_user, filters.command("unban")))
    client.add_handler(MessageHandler(handlers.promote_user, filters.command("promote")))
    client.add_handler(MessageHandler(handlers.demote_user, filters.command("demote")))
    if ENABLE_MEME_COMMAND: client.add_handler(MessageHandler(handlers.meme_command, filters.command("meme")))
    if ENABLE_GEMINI_COMMAND: client.add_handler(MessageHandler(handlers.gemini_command, filters.command("gemini")))
    if ENABLE_IMAGINE_COMMAND: client.add_handler(MessageHandler(handlers.imagine_command, filters.command("imagine")))


    # YouTube command handlers
    handlers.register_yt_handlers(client)  # Use the proper registration function

    # Register a handler for text messages that are not commands
    all_commands = [
        "start", "help", "mute", "unmute", "joindate", "usagedata", "character",
        "anime", "manga", "aghpb", "echo", "ping", "calc", "groupinfo", "pfp", "chatid", "timer",
        "timerslist", "timerdel", "reverse", "slot", "coinflip", "geekjoke", "dadjoke",
        "dog", "affirmation", "advice", "choose", "rps", "yt", "warn", "warndel", "warnsuser",
        "warnslist", "ban", "unban", "mute", "unmute", "promote", "demote"
    ]

    # Add conditional commands to the list
    if ENABLE_MEME_COMMAND:
        all_commands.append("meme")
    if ENABLE_GEMINI_COMMAND:
        all_commands.append("gemini")
    if ENABLE_IMAGINE_COMMAND:
        all_commands.append("imagine")

    client.add_handler(
        MessageHandler(
            handlers.message_event,
            filters.text & ~filters.command(all_commands)
        )
    )

    # Register a callback query handler for button clicks
    client.add_handler(CallbackQueryHandler(handlers.button_click_handler))
