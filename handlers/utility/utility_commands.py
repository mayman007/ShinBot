import datetime
import time
from tcp_latency import measure_latency
from utils.usage import save_usage

# ---------------------------
# Start command
# ---------------------------
async def start_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "start")
    sender = await event.get_sender()
    await event.reply(
        f"Hello {sender.first_name}, My name is Shin and I'm developed by @Mayman007tg.\n"
        "I'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me."
    )

# ---------------------------
# Help command
# ---------------------------
async def help_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "help")
    help_text = (
        "\nHere's my commands list:\n"
        "/advice - Get a random advice\n"
        "/affirmation - Get a random affirmation\n"
        "/aghpb - Anime girl holding programming book\n"
        "/anime - Search Anime\n"
        "/character - Search Anime & Manga characters\n"
        "/coinflip - Flip a coin\n"
        "/dadjoke - Get a random dad joke\n"
        "/dog - Get a random dog pic/vid/gif\n"
        "/echo - Repeats your words\n"
        "/geekjoke - Get a random geek joke\n"
        "/gemini - Chat with Google's Gemini Pro AI\n"
        "/help - This message\n"
        "/imagine - Generate AI images\n"
        "/joindate - Get each member's join date in the group\n"
        "/manga - Search Manga\n"
        "/meme - Get a random meme from Reddit\n"
        "/ping - Get bot's latency\n"
        "/reverse - Reverse your words\n"
        "/slot - A slot game\n"
        "/start - Bot's introduction\n"
        "/timer - Set yourself a timer\n"
        "/timerdel - Delete a timer\n"
        "/timerslist - Get a list of timers set in this chat\n"
        "/yt - Download videos from YouTube and other sites\n"
    )
    await event.reply(help_text)

# ---------------------------
# Joindate command
# ---------------------------
async def list_join_dates(event):
    chat = await event.get_chat()
    await save_usage(chat, "joindate")
    # This command must be used in a group or supergroup.
    if not event.is_group:
        await event.reply("This command can only be used in groups.")
        return

    # Check bot's admin permissions using event.client.get_permissions
    try:
        me = await event.client.get_me()
        perms = await event.client.get_permissions(event.chat_id, me.id)
    except Exception:
        await event.reply("Error: Unable to fetch bot permissions. Ensure the bot is added to the group.")
        return

    if not (perms and getattr(perms, 'is_admin', False)):
        await event.reply("Error: Bot doesn't have the necessary admin permissions. Please add it as an admin.")
        return

    # Determine if a specific member is targeted (by reply or argument)
    target_user = None
    if event.is_reply:
        try:
            reply = await event.get_reply_message()
            target_user = reply.sender_id
        except Exception:
            pass
    else:
        args = event.message.message.split()
        if len(args) > 1:
            arg = args[1].strip()
            # If the identifier starts with '@', remove it.
            if arg.startswith('@'):
                arg = arg[1:]
            # Try to interpret the argument as an integer user ID.
            try:
                target_user = int(arg)
            except ValueError:
                try:
                    # Fallback: resolve using get_entity
                    entity = await event.client.get_entity(arg)
                    target_user = entity.id
                except Exception:
                    await event.reply("Error: Unable to find a user with the provided identifier.")
                    return

    if target_user is not None:
        # Instead of using get_participant, iterate over participants to locate the target
        participant = None
        async for user in event.client.iter_participants(event.chat_id):
            if user.id == target_user:
                participant = user
                break
        if not participant:
            await event.reply("Error: Unable to retrieve the specified user's details.")
            return

        join_date = "Not Available"
        if hasattr(participant, 'participant') and getattr(participant.participant, 'date', None):
            join_date = participant.participant.date.strftime('%Y-%m-%d %H:%M:%S')
        name = participant.first_name or ""
        if participant.last_name:
            name += " " + participant.last_name
        result = f"Name: {name}\nID: {participant.id}\nJoin Date: {join_date}"
        await event.reply(result)
    else:
        # Otherwise, iterate over all members and collect their join dates.
        members = []
        async for user in event.client.iter_participants(event.chat_id):
            join_date = None
            if hasattr(user, 'participant') and getattr(user.participant, 'date', None):
                join_date = user.participant.date
                join_date_str = join_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                join_date_str = "Not Available"
            name = user.first_name or ""
            if user.last_name:
                name += " " + user.last_name
            if len(name) > 20:
                name = name[:17] + "..."
            members.append({
                'name': name,
                'id': user.id,
                'join_date': join_date,  # datetime or None
                'join_date_str': join_date_str
            })

        # Sort members: those with a join_date first (earliest first), then those without join dates.
        members.sort(key=lambda m: m['join_date'].replace(tzinfo=None)
                    if m['join_date'] is not None else datetime.datetime.max)

        # Build a mobile-friendly formatted output.
        output_lines = []
        for m in members:
            output_lines.append(f"Name: {m['name']}")
            output_lines.append(f"ID: {m['id']}")
            output_lines.append(f"Join Date: {m['join_date_str']}")
            output_lines.append("-" * 30)
        output_lines.append(f"Total Members: {len(members)}")
        output = "\n".join(output_lines)
        await event.reply(output)

# ---------------------------
# Ping Command Handler
# ---------------------------
async def ping_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "ping")
    
    try:
        initial_latency = measure_latency(host='telegram.org')
        if not initial_latency or len(initial_latency) == 0:
            initial_latency_ms = "Failed to measure"
        else:
            initial_latency_ms = f"{int(initial_latency[0])}ms"
            
        start_time = time.time()
        sent_message = await event.reply("...")
        end_time = time.time()
        round_latency = int((end_time - start_time) * 1000)
        await sent_message.edit(
            text=f"Pong!\nInitial response: `{initial_latency_ms}`\nRound-trip: `{round_latency}ms`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await event.reply(f"Error measuring latency: {str(e)}")

