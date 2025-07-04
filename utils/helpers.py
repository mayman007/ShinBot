from pyrogram import Client
from pyrogram.types import Message

async def extract_user_and_reason(client: Client, message: Message):
    """Extract user and reason from command message"""
    user = None
    reason = None
    
    # Check if replying to a message
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        # Get reason from command text
        if len(message.command) > 1:
            reason = " ".join(message.command[1:])
    else:
        # Check if user is specified in command
        if len(message.command) > 1:
            try:
                # Try to get user by username or ID
                user_identifier = message.command[1]
                if user_identifier.startswith("@"):
                    user = await client.get_users(user_identifier)
                elif user_identifier.isdigit():
                    user = await client.get_users(int(user_identifier))
                
                # Get reason if provided
                if len(message.command) > 2:
                    reason = " ".join(message.command[2:])
            except:
                pass
    
    return user, reason
