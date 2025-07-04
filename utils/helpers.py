from pyrogram import Client
from pyrogram.types import Message
import logging

logger = logging.getLogger(__name__)

async def extract_user_and_reason(client: Client, message: Message):
    """Extract target user from reply, mention, or username argument."""
    user = None
    reason = None
    
    # First check if replying to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        # Get reason from command text (everything after the command)
        command_parts = message.text.split(' ', 1)
        if len(command_parts) > 1:
            reason = command_parts[1].strip()
        return user, reason
    
    # Parse command arguments
    command_parts = message.text.split()
    if len(command_parts) < 2:
        return None, None
    
    user_identifier = command_parts[1]
    
    # Try different methods to get the user
    try:
        # Method 1: Direct username or user ID
        if user_identifier.startswith('@'):
            # Remove @ symbol
            username = user_identifier[1:]
            user = await client.get_users(username)
        elif user_identifier.isdigit():
            # User ID
            user_id = int(user_identifier)
            user = await client.get_users(user_id)
        else:
            # Try as username without @
            user = await client.get_users(user_identifier)
            
        # Get reason if provided (everything after user identifier)
        if len(command_parts) > 2:
            reason = ' '.join(command_parts[2:]).strip()
            
    except Exception as e:
        logger.warning(f"Could not get user from identifier '{user_identifier}': {e}")
        
        # Method 2: Check entities for mentions
        if message.entities:
            for entity in message.entities:
                if entity.type == "mention":
                    # Extract username from mention
                    mention_text = message.text[entity.offset:entity.offset + entity.length]
                    try:
                        user = await client.get_users(mention_text)
                        # Get reason from remaining text
                        if len(command_parts) > 2:
                            reason = ' '.join(command_parts[2:]).strip()
                        break
                    except Exception as e2:
                        logger.warning(f"Could not get user from mention '{mention_text}': {e2}")
                        continue
                elif entity.type == "text_mention":
                    # Direct user object from text mention
                    user = entity.user
                    # Get reason from remaining text
                    if len(command_parts) > 2:
                        reason = ' '.join(command_parts[2:]).strip()
                    break
    
    return user, reason
