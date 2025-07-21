import random
from pyrogram import Client, types
from utils.usage import save_usage

# ---------------------------
# Slot Command Handler
# ---------------------------
async def slot_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "slot")
    emojis = "🍎🍊🍐🍋🍉🍇🍓🍒"
    a, b, c = [random.choice(emojis) for _ in range(3)]
    
    try:
        sender = message.from_user
        sender_name = sender.first_name if sender.first_name else "User"
        slotmachine = f"**[ {a} {b} {c} ]\n{sender_name}**,"
        
        if a == b == c:
            await message.reply(f"{slotmachine} All matching, you won! 🎉")
        elif (a == b) or (a == c) or (b == c):
            await message.reply(f"{slotmachine} 2 in a row, you won! 🎉")
        else:
            await message.reply(f"{slotmachine} No match, you lost 😢")
    except Exception as e:
        await message.reply(f"Error in slot game: {str(e)}")