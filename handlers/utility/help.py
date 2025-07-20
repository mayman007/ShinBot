from pyrogram import Client, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.usage import save_usage
from config import BOT_NAME

# Command categories
COMMAND_CATEGORIES = {
    "utility": {
        "name": "🔧 Utility",
        "commands": {
            "/start": "Bot's introduction",
            "/help": "This message",
            "/ping": "Get bot's latency",
            "/yt": "Download videos from YouTube and other sites",
            "/search": "Search the internet",
            "/calc": "Calculate mathematical expressions",
            "/chatid": "Get the current chat ID",
            "/chatpfp": "Get the current chat picture",
            "/groupinfo": "Get group's info",
            "/joindate": "Get each member's join date in the group",
            "/pfp": "Get user's profile picture",
            "/feedback": "Send feedback to developers"
        }
    },
    "moderation": {
        "name": "🛡️ Moderation",
        "commands": {
            "/ban": "Ban a user",
            "/unban": "Unban a user",
            "/kick": "Kick a user",
            "/mute": "Mute a user",
            "/unmute": "Unmute a user",
            "/promote": "Promote a user to admin",
            "/demote": "Demote a user from admin",
            "/lock": "Lock chat (prevent all members from messaging)",
            "/unlock": "Unlock chat (restore messaging permissions)",
            "/warn": "Issue a warning to a user",
            "/warndel": "Delete a warning by ID",
            "/warnslist": "List all active warnings in chat",
            "/warnsuser": "View warnings for a specific user"
        }
    },
    "timer": {
        "name": "⏰ Timer",
        "commands": {
            "/timer": "Set yourself a timer",
            "/timerdel": "Delete a timer",
            "/timerslist": "Get a list of timers set in this chat"
        }
    },
    "trivia": {
        "name": "🎉 Trivia",
        "commands": {
            "/rps": "Play Rock Paper Scissors",
            "/tictactoe": "Play TicTacToe",
            "/meme": "Get a random meme from Reddit",
            "/cat": "Get a random cat pic/vid/gif",
            "/dog": "Get a random dog pic/vid/gif",
            "/slot": "A slot game",
            "/echo": "Repeats your words",
            "/reverse": "Reverse your words",
            "/choose": "Make me choose for you",
            "/coinflip": "Flip a coin",
            "/dadjoke": "Get a random dad joke",
            "/geekjoke": "Get a random geek joke",
            "/advice": "Get a random advice",
            "/affirmation": "Get a random affirmation"
        }
    },
    "anime": {
        "name": "🖼️ Anime & Manga",
        "commands": {
            "/anime": "Search Anime",
            "/manga": "Search Manga",
            "/character": "Search Anime & Manga characters",
            "/aghpb": "Anime girl holding programming book"
        }
    },
    "ai": {
        "name": "🤖 AI",
        "commands": {
            "/gemini": "Chat with Google's Gemini Pro AI",
            "/imagine": "Generate AI images"
        }
    }
}

async def help_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "help")
    
    # Check if user wants moderation commands only (legacy support)
    args = message.text.split()
    if len(args) > 1 and args[1].lower() == "mod":
        await show_category_commands(message, "moderation")
        return
    
    # Show main help menu with category buttons
    await show_help_menu(message)

async def show_help_menu(message):
    help_text = (
        f"🤖 **{BOT_NAME} Help Menu**\n\n"
        "Welcome! I'm an all-in-one multipurpose bot with many features.\n"
        "Select a category below to see available commands:"
    )
    
    # Create category buttons in rows of 2
    keyboard = []
    categories = list(COMMAND_CATEGORIES.items())
    
    for i in range(0, len(categories), 2):
        row = []
        # Add first button
        category_id, category_data = categories[i]
        row.append(InlineKeyboardButton(
            category_data["name"], 
            callback_data=f"help_category:{category_id}"
        ))
        
        # Add second button if it exists
        if i + 1 < len(categories):
            category_id, category_data = categories[i + 1]
            row.append(InlineKeyboardButton(
                category_data["name"], 
                callback_data=f"help_category:{category_id}"
            ))
        
        keyboard.append(row)
    
    # Add "All Commands" button
    keyboard.append([
        InlineKeyboardButton("📋 All Commands", callback_data="help_all")
    ])
    
    markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await message.edit_text(help_text, reply_markup=markup)
    except:
        await message.reply(help_text, reply_markup=markup)

async def show_category_commands(message, category_id):
    if category_id not in COMMAND_CATEGORIES:
        await message.edit_text("❌ Category not found.")
        return
    
    category_data = COMMAND_CATEGORIES[category_id]
    
    help_text = f"{category_data['name']} **Commands:**\n\n"
    
    for command, description in category_data["commands"].items():
        help_text += f"{command} - {description}\n"
    
    # Back button
    keyboard = [[
        InlineKeyboardButton("⬅️ Back to Menu", callback_data="help_back")
    ]]
    
    markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await message.edit_text(help_text, reply_markup=markup)
    except:
        await message.reply(help_text, reply_markup=markup)

async def show_all_commands(message):
    help_text = f"🤖 **{BOT_NAME} - All Commands**\n\n"
    
    for category_id, category_data in COMMAND_CATEGORIES.items():
        help_text += f"{category_data['name']}:\n"
        for command, description in category_data["commands"].items():
            help_text += f"{command} - {description}\n"
        help_text += "\n"
    
    # Back button
    keyboard = [[
        InlineKeyboardButton("⬅️ Back to Menu", callback_data="help_back")
    ]]
    
    markup = InlineKeyboardMarkup(keyboard)
    
    # Split message if too long
    if len(help_text) > 4096:
        help_text = help_text[:4090] + "..."
    
    try:
        await message.edit_text(help_text, reply_markup=markup)
    except:
        await message.reply(help_text, reply_markup=markup)

async def handle_help_callback(client: Client, callback_query):
    data = callback_query.data
    
    if data.startswith("help_category:"):
        category_id = data.split(":", 1)[1]
        await show_category_commands(callback_query.message, category_id)
        await callback_query.answer()
    
    elif data == "help_all":
        await show_all_commands(callback_query.message)
        await callback_query.answer()
    
    elif data == "help_back":
        await show_help_menu(callback_query.message)
        await callback_query.answer()
    
    else:
        await callback_query.answer("Unknown action", show_alert=False)
