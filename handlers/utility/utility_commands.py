import time
import math
import re
import asyncio
from pyrogram import Client, types
from tcp_latency import measure_latency
from utils.usage import save_usage

# ---------------------------
# Start command
# ---------------------------
async def start_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "start")
    sender = message.from_user
    await message.reply(
        f"Hello {sender.first_name}, My name is Shin and I'm developed by @Mayman007tg.\n"
        "I'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me."
    )

# ---------------------------
# Help command
# ---------------------------
async def help_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "help")
    
    # Check if user wants moderation commands only
    args = message.text.split()
    if len(args) > 1 and args[1].lower() == "mod":
        mod_help_text = (
            "\nHere's my moderation commands list:\n"
            "/ban - Ban a user\n"
            "/demote - Demote a user from admin\n"
            "/kick - Kick a user\n"
            "/mute - Mute a user\n"
            "/promote - Promote a user to admin\n"
            "/unban - Unban a user\n"
            "/unmute - Unmute a user\n"
            "/warn - Issue a warning to a user\n"
            "/warndel - Delete a warning by ID\n"
            "/warnslist - List all active warnings in chat\n"
            "/warnsuser - View warnings for a specific user\n"
        )
        await message.reply(mod_help_text)
        return
    
    help_text = (
        "\nHere's my commands list:\n"
        "/advice - Get a random advice\n"
        "/affirmation - Get a random affirmation\n"
        "/aghpb - Anime girl holding programming book\n"
        "/anime - Search Anime\n"
        "/ban - Ban a user\n"
        "/calc - Calculate mathematical expressions\n"
        "/character - Search Anime & Manga characters\n"
        "/chatid - Get the current chat ID\n"
        "/choose - Make me choose for you\n"
        "/coinflip - Flip a coin\n"
        "/dadjoke - Get a random dad joke\n"
        "/demote - Demote a user from admin\n"
        "/dog - Get a random dog pic/vid/gif\n"
        "/echo - Repeats your words\n"
        "/geekjoke - Get a random geek joke\n"
        "/gemini - Chat with Google's Gemini Pro AI\n"
        "/groupinfo - Get group's info\n"
        "/help - This message\n"
        "/imagine - Generate AI images\n"
        "/joindate - Get each member's join date in the group\n"
        "/kick - Kick a user\n"
        "/manga - Search Manga\n"
        "/meme - Get a random meme from Reddit\n"
        "/mute - Mute a user\n"
        "/pfp - Get user's profile picture\n"
        "/ping - Get bot's latency\n"
        "/promote - Promote a user to admin\n"
        "/reverse - Reverse your words\n"
        "/rps - Play Rock Paper Scissors\n"
        "/slot - A slot game\n"
        "/start - Bot's introduction\n"
        "/timer - Set yourself a timer\n"
        "/timerdel - Delete a timer\n"
        "/timerslist - Get a list of timers set in this chat\n"
        "/unban - Unban a user\n"
        "/unmute - Unmute a user\n"
        "/warn - Issue a warning to a user\n"
        "/warndel - Delete a warning by ID\n"
        "/warnslist - List all active warnings in chat\n"
        "/warnsuser - View warnings for a specific user\n"
        "/yt - Download videos from YouTube and other sites\n"
    )
    await message.reply(help_text)

# ---------------------------
# Ping Command Handler
# ---------------------------
async def ping_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "ping")
    
    try:
        # Measure bot response time (message processing + API call)
        start_time = time.time()
        sent_message = await message.reply("🏓 Measuring...")
        bot_response_time = int((time.time() - start_time) * 1000)
        
        # Measure network latency to Telegram servers
        try:
            telegram_latency = measure_latency(host='149.154.167.50', port=443, timeout=5)  # Telegram server IP
            if not telegram_latency or len(telegram_latency) == 0:
                network_latency_ms = "Failed"
            else:
                network_latency_ms = f"{int(telegram_latency[0])}ms"
        except:
            network_latency_ms = "Failed"
        
        # Final result
        await sent_message.edit_text(
            f"🏓 **Pong!**\n\n"
            f"**Bot Response:** `{bot_response_time}ms`\n"
            f"**Network:** `{network_latency_ms}`"
        )
        
    except Exception as e:
        await message.reply(f"❌ Error measuring latency: {str(e)}")

# ---------------------------
# Calculator command
# ---------------------------
async def calc_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "calc")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /calc <expression>\nExample: /calc 2 + 2 * 3\nSupports: +, -, *, /, %, ^ (power), ! (factorial), sin, cos, tan, log, sqrt, pi, e")
        return
    
    expression = args[1].strip()
    
    # Limit expression length to prevent abuse
    if len(expression) > 200:
        await message.reply("Error: Expression too long (max 200 characters)")
        return
    
    try:
        # Check for factorial abuse before processing
        factorial_matches = re.findall(r'(\d+)!', expression)
        for match in factorial_matches:
            if int(match) > 20:
                await message.reply("Error: Factorial input too large (max 20!)")
                return
        
        # Replace ^ with ** for exponentiation
        expression = re.sub(r'\^', '**', expression)
        
        # Replace factorial notation (e.g., 5! becomes math.factorial(5))
        expression = re.sub(r'(\d+)!', r'math.factorial(\1)', expression)
        
        # Replace common math functions with math module equivalents
        expression = re.sub(r'\bsin\b', 'math.sin', expression)
        expression = re.sub(r'\bcos\b', 'math.cos', expression)
        expression = re.sub(r'\btan\b', 'math.tan', expression)
        expression = re.sub(r'\blog\b', 'math.log', expression)
        expression = re.sub(r'\bsqrt\b', 'math.sqrt', expression)
        expression = re.sub(r'\bpi\b', 'math.pi', expression)
        expression = re.sub(r'\be\b', 'math.e', expression)
        
        # Use eval with restricted globals for safety
        allowed_names = {
            "__builtins__": {},
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
        }
        
        # Use asyncio timeout for cross-platform compatibility
        async def evaluate_expression():
            return eval(expression, allowed_names, {})
        
        try:
            result = await asyncio.wait_for(evaluate_expression(), timeout=5.0)
        except asyncio.TimeoutError:
            await message.reply("Error: Calculation timeout (too complex)")
            return
        
        # Check if result is too large
        if isinstance(result, (int, float)) and abs(result) > 1e15:
            await message.reply("Error: Result too large to display")
            return
        
        # Format the result nicely
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)
        
        await message.reply(f"**Expression:** `{args[1]}`\n**Result:** `{result}`")
        
    except ZeroDivisionError:
        await message.reply("Error: Division by zero!")
    except (SyntaxError, NameError, TypeError, ValueError) as e:
        await message.reply(f"Error: Invalid expression. {str(e)}")
    except Exception as e:
        await message.reply(f"Error: {str(e)}")
