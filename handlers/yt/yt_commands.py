import os
import time
import logging
from pyrogram import Client, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.usage import save_usage
from .constants import active_downloads, DOWNLOADS_DIR
from .format_utils import extract_info, list_video_options, list_audio_options
from .file_utils import sanitize_filename

logger = logging.getLogger(__name__)

async def yt_command(client: Client, message: types.Message):
    """Handle /yt command for downloading YouTube videos."""
    chat = message.chat
    await save_usage(chat, "yt")
    
    user_id = message.from_user.id
    
    if user_id in active_downloads:
        await message.reply(f"⚠️ You already have an active download in progress:\n\n{active_downloads[user_id]}\n\nPlease wait for it to complete before starting a new one.")
        return
        
    message_text = message.text
    args = message_text.split()[1:]
    
    if not args:
        await message.reply('Usage: /yt [video url] (+ "subs" if wanted)')
        return

    subs_requested = "subs" in [arg.lower() for arg in args]
    video_url = None
    for arg in args:
        if arg.startswith("http"):
            video_url = arg
            break

    if not video_url:
        await message.reply("No valid video URL provided.")
        return

    if subs_requested:
        status_msg = await message.reply("Fetching subtitle info, please wait...")
        try:
            info = await extract_info(video_url)
            safe_title = sanitize_filename(info.get("title", "subtitle"))
            
            subs_data = {}
            
            if info.get("subtitles"):
                for lang, tracks in info["subtitles"].items():
                    if "live_chat" in lang.lower():
                        continue
                    subs_data[lang] = tracks
                    
            if info.get("automatic_captions"):
                for lang, tracks in info["automatic_captions"].items():
                    if "live_chat" in lang.lower():
                        continue
                    if tracks and lang.lower().startswith("en"):
                        auto_key = f"{lang} (auto-generated)"
                        if auto_key not in subs_data:
                            subs_data[auto_key] = tracks
            
            subs_data = {lang: tracks for lang, tracks in subs_data.items() if tracks}
            
            if not subs_data:
                await status_msg.edit("No subtitles available for this video.")
                return
            
            buttons = []
            for lang in sorted(subs_data.keys()):
                buttons.append([InlineKeyboardButton(lang, callback_data=f"subs_{lang}")])
                
            if not hasattr(client, 'user_data'):
                client.user_data = {}
                
            client.user_data[f"subs_data_{message.chat.id}_{message.from_user.id}"] = {
                'video_url': video_url,
                'safe_title': safe_title,
                'original_msg_id': message.id,
            }
            
            await status_msg.edit("Choose subtitle language:", reply_markup=InlineKeyboardMarkup(buttons))
            
        except Exception as e:
            await status_msg.edit(f"Error fetching subtitle info: {str(e)}")
        return

    status_msg = await message.reply("Fetching video info, please wait...")
    
    try:
        info, video_options, best_audio = await list_video_options(video_url)
        
        if not hasattr(client, 'user_data'):
            client.user_data = {}
            
        user_data_key = f"yt_data_{message.chat.id}_{message.from_user.id}"
        client.user_data[user_data_key] = {
            'video_url': video_url,
            'options': video_options,
            'best_audio': best_audio,
            'message_id': status_msg.id,
            'original_msg_id': message.id,
        }
        
        buttons = []
        buttons.append([InlineKeyboardButton("🎥 Video Options:", callback_data="ignore")])
        for i, option in enumerate(video_options):
            resolution = option['resolution']
            stream_type = option['stream_type']
            size = option['total_size']
            size_str = f"{size/(1024*1024):.1f} MB" if size else "N/A"
            button_text = f"{resolution} ({stream_type}, {size_str})"
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"yt_{i}")])
        
        audio_options = await list_audio_options(video_url)
        if audio_options:
            buttons.append([InlineKeyboardButton("🎵 Audio Options:", callback_data="ignore")])
            for i, option in enumerate(audio_options):
                abr = option["abr"]
                size = option["filesize"]
                size_str = f"{size/(1024*1024):.1f} MB"
                button_text = f"{abr} kbps ({size_str})"
                buttons.append([InlineKeyboardButton(button_text, callback_data=f"yt_audio_{i}")])
                
            client.user_data[f"yt_audio_{message.chat.id}_{message.from_user.id}"] = audio_options
        
        video_title = info.get('title', 'Video')
        await status_msg.edit(f"Choose quality for: {video_title}", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await status_msg.edit(f"Error: {str(e)}")

async def cleanup_downloads(client: Client, message: types.Message):
    """Admin command to clean up old downloads."""
    if not await is_admin_or_owner(client, message.from_user.id):
        await message.reply("You don't have permission to use this command.")
        return
    
    try:
        cutoff_time = time.time() - 86400  # 24 hours
        deleted_count = 0
        
        for user_dir in os.listdir(DOWNLOADS_DIR):
            user_path = os.path.join(DOWNLOADS_DIR, user_dir)
            if not os.path.isdir(user_path):
                continue
                
            for file in os.listdir(user_path):
                file_path = os.path.join(user_path, file)
                if os.path.isfile(file_path):
                    file_time = os.path.getmtime(file_path)
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
        
        await message.reply(f"Cleanup complete. Deleted {deleted_count} old files.")
    except Exception as e:
        await message.reply(f"Error during cleanup: {str(e)}")

async def is_admin_or_owner(client: Client, user_id):
    """Check if user is an admin or the bot owner."""
    try:
        from config import ADMIN_IDS
        if user_id in ADMIN_IDS:
            return True
    except ImportError:
        pass
        
    return False