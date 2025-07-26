import asyncio
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
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
    
    # Check entities first for mentions (handles text mentions and @ mentions)
    if message.entities:
        logger.debug(f"Found {len(message.entities)} entities in message: {message.text}")
        for entity in message.entities:
            logger.debug(f"Entity type: {entity.type}, offset: {entity.offset}, length: {entity.length}")
            if entity.type == "mention":
                # Extract username from mention (with @)
                mention_text = message.text[entity.offset:entity.offset + entity.length]
                try:
                    user = await client.get_users(mention_text)
                    # Get reason from text after the mention
                    # Handle cases where there might be punctuation after mention
                    after_mention = message.text[entity.offset + entity.length:].strip()
                    if after_mention.startswith(','):
                        after_mention = after_mention[1:].strip()
                    if after_mention:
                        reason = after_mention
                    break
                except Exception as e:
                    logger.warning(f"Could not get user from mention '{mention_text}': {e}")
                    continue
            elif entity.type == "text_mention":
                # Direct user object from text mention (no @ symbol, contact name)
                logger.debug(f"Found text_mention for user: {entity.user.first_name if entity.user else 'None'}")
                user = entity.user
                # Get reason from text after the mention
                after_mention = message.text[entity.offset + entity.length:].strip()
                if after_mention.startswith(','):
                    after_mention = after_mention[1:].strip()
                if after_mention:
                    reason = after_mention
                break
    
    # If user found from entities, return early
    if user:
        logger.debug(f"User found from entities: {user.first_name}")
        return user, reason
    
    # Parse command arguments as fallback
    logger.debug("No user found from entities, trying command arguments")
    command_parts = message.text.split()
    if len(command_parts) < 2:
        return None, None
    
    user_identifier = command_parts[1]
    
    # Clean the user identifier from trailing punctuation
    if user_identifier.startswith('@'):
        # Remove @ symbol and clean trailing punctuation
        username = user_identifier[1:].rstrip('.,!?;:')
        user_identifier = username
    else:
        # Clean trailing punctuation for non-@ identifiers too
        user_identifier = user_identifier.rstrip('.,!?;:')
    
    # Skip username resolution if it looks like a display name or contains spaces
    if not command_parts[1].startswith('@') and not user_identifier.isdigit():
        # Check if this looks like a display name (contains non-ASCII or spaces in full text)
        full_name_text = ' '.join(command_parts[1:])
        if ' ' in full_name_text or any(ord(char) > 127 for char in user_identifier):
            logger.debug(f"Skipping username resolution for apparent display name: '{full_name_text}'")
            return None, None
    
    # Try different methods to get the user
    try:
        # Method 1: Direct username or user ID
        if command_parts[1].startswith('@'):
            # Use cleaned username
            user = await client.get_users(user_identifier)
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
        logger.warning(f"Could not get user from identifier '{command_parts[1]}': {e}")
    
    return user, reason

async def split_text_into_pages(lines, max_length=1000):
    """Split text lines into pages that fit within message limits."""
    pages = []
    current_page = ""
    
    for i, line in enumerate(lines):
        # Yield control every 50 lines for very large datasets
        if i % 50 == 0:
            await asyncio.sleep(0)
            
        # Check if adding this line would exceed the limit
        if len(current_page) + len(line) + 2 > max_length and current_page:
            pages.append(current_page.strip())
            current_page = line
        else:
            if current_page:
                current_page += "\n" + line
            else:
                current_page = line
    
    # Add the last page
    if current_page:
        pages.append(current_page.strip())
    
    return pages

async def create_pagination_keyboard(current_page, total_pages, callback_prefix):
    """Create pagination keyboard with Previous/Next buttons."""
    keyboard = []
    buttons = []
    
    # Previous button
    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            "◀️ Previous", 
            callback_data=f"{callback_prefix}_{current_page - 1}"
        ))
    
    # Page indicator
    buttons.append(InlineKeyboardButton(
        f"{current_page}/{total_pages}", 
        callback_data="ignore"
    ))
    
    # Next button
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(
            "Next ▶️", 
            callback_data=f"{callback_prefix}_{current_page + 1}"
        ))
    
    if buttons:
        keyboard.append(buttons)
    
    return InlineKeyboardMarkup(keyboard) if keyboard else None