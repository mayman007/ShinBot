import os
import re
import glob
import asyncio
import yt_dlp
from io import BytesIO
from telethon import TelegramClient, events, Button
from typing import Dict, List, Optional, Any, Tuple

# Constants
MAX_FILESIZE = 2147483648  # 2GB max file size for Telegram
COOKIES_FILE = 'cookies.txt'
DOWNLOADS_DIR = 'downloads'

# Ensure downloads directory exists
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Helper functions
def add_cookies_to_opts(opts: dict) -> dict:
    """Add cookies to yt-dlp options if cookie file exists."""
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    if 'restrictfilenames' not in opts:
        opts['restrictfilenames'] = True
    return opts

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename and trim length."""
    if not filename:
        return "unnamed_file"
    sanitized = re.sub(r'[<>:"/\\|?*\uFF1A]', '', filename)
    sanitized = sanitized.strip().rstrip('.')
    return sanitized[:100] if len(sanitized) > 100 else sanitized

def safe_delete(filepath: str) -> None:
    """Safely delete a file if it exists."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error deleting file {filepath}: {e}")

def get_best_audio(info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get the best audio format from video info."""
    if not info:
        return None
    
    audio_formats = [
        fmt for fmt in info.get('formats', [])
        if fmt.get('vcodec') == 'none' and (fmt.get('filesize') or fmt.get('filesize_approx'))
    ]
    
    return max(audio_formats, key=lambda f: f.get('filesize') or f.get('filesize_approx'), default=None) if audio_formats else None

def get_resolution(fmt: Dict[str, Any]) -> str:
    """Get formatted resolution string from format info."""
    if fmt.get('resolution'):
        return fmt['resolution']
    elif fmt.get('height'):
        return f"{fmt['height']}p"
    else:
        return "N/A"

def get_size(fmt: Dict[str, Any]) -> Optional[int]:
    """Get size from format info in bytes."""
    return fmt.get('filesize') or fmt.get('filesize_approx')

async def extract_info(url: str, download: bool = False) -> Dict[str, Any]:
    """Extract video info using yt-dlp with error handling."""
    try:
        with yt_dlp.YoutubeDL(add_cookies_to_opts({'quiet': True})) as ydl:
            return await asyncio.to_thread(ydl.extract_info, url, download)
    except yt_dlp.utils.DownloadError as e:
        raise ValueError(f"Error extracting video info: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")

async def list_video_options(url: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """List available video formats with sizes and resolutions."""
    info = await extract_info(url)
    best_audio = get_best_audio(info)
    
    candidates = []
    for fmt in info.get('formats', []):
        if fmt.get('ext') != 'mp4' or fmt.get('vcodec') == 'none':
            continue
            
        resolution = get_resolution(fmt)
        video_size = get_size(fmt)
        
        if video_size is None:
            continue
            
        if fmt.get('acodec') != 'none':
            total_size = video_size
            stream_type = "Progressive"
        else:
            stream_type = "Adaptive"
            audio_size = get_size(best_audio) if best_audio else None
            total_size = video_size + audio_size if audio_size is not None else video_size
            
        candidates.append({
            'format': fmt,
            'resolution': resolution,
            'stream_type': stream_type,
            'video_size': video_size,
            'total_size': total_size,
        })
    
    # Group by resolution and select best quality for each
    grouped = {}
    for cand in candidates:
        res = cand['resolution']
        if res in grouped:
            existing = grouped[res]
            if (cand['total_size'] is not None and existing['total_size'] is not None and
                cand['total_size'] > existing['total_size']):
                grouped[res] = cand
            elif cand['total_size'] is not None and existing['total_size'] is None:
                grouped[res] = cand
        else:
            grouped[res] = cand
    
    video_options = list(grouped.values())
    # Sort by height for consistent order
    video_options.sort(key=lambda c: int(c['format'].get('height') or 0))
    
    return info, video_options, best_audio

async def list_audio_options(url: str) -> List[Dict[str, Any]]:
    """List available audio formats with bitrates and sizes."""
    info = await extract_info(url)
    
    audio_candidates = []
    for fmt in info.get("formats", []):
        if fmt.get("vcodec") != "none":
            continue
            
        size = fmt.get("filesize") or fmt.get("filesize_approx")
        if not size:
            continue
            
        abr = fmt.get("abr")
        if not abr:
            continue
            
        audio_candidates.append({
            "format": fmt,
            "abr": abr,
            "filesize": size,
        })
    
    # Group by bitrate and select best quality for each
    unique = {}
    for candidate in audio_candidates:
        key = candidate["abr"]
        if key in unique:
            if candidate["filesize"] > unique[key]["filesize"]:
                unique[key] = candidate
        else:
            unique[key] = candidate
    
    options = list(unique.values())
    options.sort(key=lambda c: c["abr"], reverse=True)
    
    return options

async def download_video(url: str, video_format_id: str, best_audio: Optional[Dict[str, Any]], 
                        stream_type: str, resolution: str) -> Tuple[str, str]:
    """Download video at specified quality."""
    info = await extract_info(url)
    safe_title = sanitize_filename(info.get("title", "video"))
    
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    expected_filename = os.path.join(DOWNLOADS_DIR, f"{safe_title} - {resolution}.mp4")
    
    if stream_type == "Adaptive" and best_audio:
        fmt_str = f"{video_format_id}+{best_audio.get('format_id')}"
    else:
        fmt_str = video_format_id
    
    ydl_opts = add_cookies_to_opts({
        'format': fmt_str,
        'merge_output_format': 'mp4',
        'windowsfilenames': True,
        'outtmpl': expected_filename,
        'max_filesize': MAX_FILESIZE,
        'postprocessor_args': ['-c:a', 'aac'],
    })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.extract_info, url, download=True)
        
        if not os.path.exists(expected_filename):
            # Try to find the actual file if outtmpl didn't work as expected
            pattern = os.path.join(DOWNLOADS_DIR, f"{safe_title}*.mp4")
            matches = glob.glob(pattern)
            if matches:
                expected_filename = matches[0]
    except Exception as e:
        raise ValueError(f"Error downloading video: {str(e)}")
        
    return expected_filename, safe_title

async def download_audio_by_format(url: str, audio_format_id: str, quality_str: str) -> Tuple[str, str]:
    """Download audio at specified quality."""
    info = await extract_info(url)
    safe_title = sanitize_filename(info.get("title", "audio"))
    
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    expected_template = os.path.join(DOWNLOADS_DIR, f"{safe_title}.{quality_str}.%(ext)s")
    expected_filename = os.path.join(DOWNLOADS_DIR, f"{safe_title}.{quality_str}.mp3")
    
    ydl_opts = add_cookies_to_opts({
        'format': audio_format_id,
        'windowsfilenames': True,
        'outtmpl': expected_template,
        'max_filesize': MAX_FILESIZE,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        
        if not os.path.exists(expected_filename):
            # Try to find the actual file if outtmpl didn't work as expected
            pattern = os.path.join(DOWNLOADS_DIR, f"{safe_title}*.mp3")
            matches = glob.glob(pattern)
            if matches:
                expected_filename = matches[0]
    except Exception as e:
        raise ValueError(f"Error downloading audio: {str(e)}")
        
    return expected_filename, safe_title

async def download_subtitles(url: str, lang: str, safe_title: str) -> Optional[str]:
    """Download subtitles in specified language."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    outtmpl = os.path.join(DOWNLOADS_DIR, safe_title)
    
    # Handle language formatting
    sub_lang = lang
    if "auto-generated" in lang:
        # Extract the actual language code from the auto-generated string
        sub_lang = lang.split(" ")[0]
    
    # Use more flexible language pattern to increase chances of finding subtitles
    ydl_opts = add_cookies_to_opts({
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': [sub_lang],
        'subtitlesformat': 'srt',
        'outtmpl': outtmpl,
        'quiet': True,
    })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
    except Exception as e:
        print(f"Error downloading subtitles: {e}")
        return None
    
    # Try different patterns to find the subtitle file
    pattern = os.path.join(DOWNLOADS_DIR, f"{safe_title}.{sub_lang}.*")
    matches = glob.glob(pattern)
    
    if not matches:
        # Try alternative pattern
        pattern = os.path.join(DOWNLOADS_DIR, f"{safe_title}.*.{sub_lang}.*")
        matches = glob.glob(pattern)
        
    if matches:
        return matches[0]
    else:
        return None

# Command handlers for Telethon

@events.register(events.NewMessage(pattern=r'/yt'))
async def yt_command(event):
    """Handle /yt command for downloading YouTube videos."""
    message_text = event.message.message
    args = message_text.split()[1:]  # Skip the command itself
    
    if not args:
        await event.reply("Usage: /yt <video URL> [subs]")
        return

    # Parse arguments
    subs_requested = "subs" in [arg.lower() for arg in args]
    video_url = None
    for arg in args:
        if arg.startswith("http"):
            video_url = arg
            break

    if not video_url:
        await event.reply("No valid video URL provided.")
        return

    # Check if subtitle info is requested
    if subs_requested:
        status_msg = await event.reply("Fetching subtitle info, please wait...")
        try:
            info = await extract_info(video_url)
            safe_title = sanitize_filename(info.get("title", "subtitle"))
            
            # Collect subtitle information
            subs_data = {}
            
            # Process regular subtitles
            if info.get("subtitles"):
                for lang, tracks in info["subtitles"].items():
                    if "live_chat" in lang.lower():
                        continue
                    subs_data[lang] = tracks
                    
            # Process automatic captions
            if info.get("automatic_captions"):
                for lang, tracks in info["automatic_captions"].items():
                    if "live_chat" in lang.lower():
                        continue
                    if tracks and lang.lower().startswith("en"):
                        auto_key = f"{lang} (auto-generated)"
                        if auto_key not in subs_data:
                            subs_data[auto_key] = tracks
            
            # Filter out empty tracks
            subs_data = {lang: tracks for lang, tracks in subs_data.items() if tracks}
            
            if not subs_data:
                await status_msg.edit("No subtitles available for this video.")
                return
            
            # Create buttons for each subtitle language
            buttons = []
            for lang in sorted(subs_data.keys()):
                buttons.append([Button.inline(lang, data=f"subs_{lang}")])
                
            # Store subtitle data in user_data
            if not hasattr(event.client, 'user_data'):
                event.client.user_data = {}
                
            event.client.user_data[f"subs_data_{event.chat_id}_{event.sender_id}"] = {
                'video_url': video_url,
                'safe_title': safe_title,
            }
            
            await status_msg.edit("Choose subtitle language:", buttons=buttons)
            
        except Exception as e:
            await status_msg.edit(f"Error fetching subtitle info: {str(e)}")
        return

    # Handle video/audio download
    status_msg = await event.reply("Fetching video info, please wait...")
    
    try:
        # Get video format options
        info, video_options, best_audio = await list_video_options(video_url)
        
        # Initialize user_data if not already available
        if not hasattr(event.client, 'user_data'):
            event.client.user_data = {}
            
        # Store data for callback
        user_data_key = f"yt_data_{event.chat_id}_{event.sender_id}"
        event.client.user_data[user_data_key] = {
            'video_url': video_url,
            'options': video_options,
            'best_audio': best_audio,
            'message_id': status_msg.id,
        }
        
        # Create buttons for video options
        buttons = []
        for i, option in enumerate(video_options):
            resolution = option['resolution']
            stream_type = option['stream_type']
            size = option['total_size']
            size_str = f"{size/(1024*1024):.1f} MB" if size else "N/A"
            button_text = f"{resolution} ({stream_type}, {size_str})"
            buttons.append([Button.inline(button_text, data=f"yt_{i}")])
        
        # Get audio options
        audio_options = await list_audio_options(video_url)
        if audio_options:
            buttons.append([Button.inline("🎵 Audio Options:", data="ignore")])
            for i, option in enumerate(audio_options):
                abr = option["abr"]
                size = option["filesize"]
                size_str = f"{size/(1024*1024):.1f} MB"
                button_text = f"{abr} kbps ({size_str})"
                buttons.append([Button.inline(button_text, data=f"yt_audio_{i}")])
                
            # Store audio options
            event.client.user_data[f"yt_audio_{event.chat_id}_{event.sender_id}"] = audio_options
        
        video_title = info.get('title', 'Video')
        await status_msg.edit(f"Choose quality for: {video_title}", buttons=buttons)
        
    except Exception as e:
        await status_msg.edit(f"Error: {str(e)}")

@events.register(events.CallbackQuery(pattern=r'yt_\d+$'))
async def yt_quality_button(event):
    """Handle video quality selection callback."""
    try:
        await event.answer()  # Acknowledge callback
        
        # Extract index from callback data
        index = int(event.data.decode().split("_")[1])
        
        # Get user data
        user_data_key = f"yt_data_{event.chat_id}_{event.sender_id}"
        yt_data = getattr(event.client, 'user_data', {}).get(user_data_key)
        
        if not yt_data:
            await event.edit("Session expired. Please use /yt command again.")
            return
        
        video_url = yt_data['video_url']
        options = yt_data['options']
        best_audio = yt_data['best_audio']
        
        if index < 0 or index >= len(options):
            await event.edit("Invalid selection.")
            return
        
        selected = options[index]
        resolution = selected['resolution']
        video_format_id = selected['format'].get('format_id')
        stream_type = selected['stream_type']
        
        # Update message to show download progress
        await event.edit(f"Downloading video at {resolution}... Please wait, this may take some time.")
        
        try:
            # Download the video
            filename, safe_title = await download_video(video_url, video_format_id, best_audio, stream_type, resolution)
            
            # Check file size before sending
            file_size = os.path.getsize(filename)
            if file_size > MAX_FILESIZE:
                await event.edit(f"Error: File size ({file_size/(1024*1024):.1f} MB) exceeds Telegram's limit of 2 GB.")
                safe_delete(filename)
                return
                
            # Upload progress message
            await event.edit(f"Uploading video {resolution}... Please wait.")
            
            # Send the file
            await event.client.send_file(
                entity=event.chat_id,
                file=filename,
                caption=f"{safe_title} [{resolution}]",
                reply_to=yt_data.get('message_id'),
                supports_streaming=True,
            )
            
            # Clean up the file and button
            safe_delete(filename)
            await event.delete()
            
        except Exception as e:
            await event.edit(f"Error: {str(e)}")
            # Clean up any partially downloaded files
            pattern = os.path.join(DOWNLOADS_DIR, f"*{resolution}*")
            for file in glob.glob(pattern):
                safe_delete(file)
            
    except Exception as e:
        await event.edit(f"An unexpected error occurred: {str(e)}")

@events.register(events.CallbackQuery(pattern=r'yt_audio_\d+$'))
async def yt_audio_button(event):
    """Handle audio quality selection callback."""
    try:
        await event.answer()  # Acknowledge callback
        
        # Extract index from callback data
        index = int(event.data.decode().split("_")[2])
        
        # Get audio options from user data
        audio_key = f"yt_audio_{event.chat_id}_{event.sender_id}"
        audio_options = getattr(event.client, 'user_data', {}).get(audio_key)
        
        if not audio_options or index < 0 or index >= len(audio_options):
            await event.edit("Session expired or invalid selection. Please use /yt command again.")
            return
        
        selected = audio_options[index]
        
        # Get the video URL from the main data
        data_key = f"yt_data_{event.chat_id}_{event.sender_id}"
        main_data = getattr(event.client, 'user_data', {}).get(data_key, {})
        video_url = main_data.get("video_url")
        
        if not video_url:
            await event.edit("Session expired. Please use /yt command again.")
            return
        
        audio_format_id = selected["format"].get("format_id")
        quality_str = f"{selected['abr']}kbps"
        
        # Update message to show download progress
        await event.edit(f"Downloading audio at {selected['abr']} kbps... Please wait.")
        
        try:
            # Download the audio
            filename, safe_title = await download_audio_by_format(video_url, audio_format_id, quality_str)
            
            # Check if file exists
            if not os.path.exists(filename):
                await event.edit("Error: Downloaded file not found.")
                return
                
            # Check file size
            file_size = os.path.getsize(filename)
            if file_size > MAX_FILESIZE:
                await event.edit(f"Error: File size ({file_size/(1024*1024):.1f} MB) exceeds Telegram's limit.")
                safe_delete(filename)
                return
                
            # Upload progress message
            await event.edit(f"Uploading audio {selected['abr']} kbps... Please wait.")
            
            # Read file into memory to avoid potential file locking issues
            with open(filename, "rb") as f:
                file_data = f.read()
                
            # Create BytesIO object
            bio = BytesIO(file_data)
            bio.name = os.path.basename(filename)
            
            # Send the file
            await event.client.send_file(
                entity=event.chat_id,
                file=bio,
                caption=f"{safe_title} - {selected['abr']} kbps",
                reply_to=main_data.get('message_id'),
            )
            
            # Clean up the file and button
            safe_delete(filename)
            await event.delete()
            
        except Exception as e:
            await event.edit(f"Error: {str(e)}")
            # Clean up any partially downloaded files
            pattern = os.path.join(DOWNLOADS_DIR, f"*{quality_str}*")
            for file in glob.glob(pattern):
                safe_delete(file)
            
    except Exception as e:
        await event.edit(f"An unexpected error occurred: {str(e)}")

@events.register(events.CallbackQuery(pattern=r'subs_'))
async def yt_subs_callback(event):
    """Handle subtitle language selection callback."""
    try:
        await event.answer()  # Acknowledge callback
        
        # Extract language from callback data
        lang = event.data.decode().split("_", 1)[1]
        
        # Get subtitle data from user data
        subs_key = f"subs_data_{event.chat_id}_{event.sender_id}"
        subs_data = getattr(event.client, 'user_data', {}).get(subs_key)
        
        if not subs_data:
            await event.edit("Session expired. Please use /yt command with subs again.")
            return
        
        video_url = subs_data['video_url']
        safe_title = subs_data['safe_title']
        
        # Update message to show download progress
        await event.edit(f"Downloading subtitles for language: {lang}...")
        
        try:
            # Download subtitles
            filename = await download_subtitles(video_url, lang, safe_title)
            
            if not filename or not os.path.exists(filename):
                await event.edit(f"Error: Subtitles for {lang} not available or could not be downloaded.")
                return
                
            # Check file size
            file_size = os.path.getsize(filename)
            if file_size == 0:
                await event.edit(f"Error: Downloaded subtitle file is empty.")
                safe_delete(filename)
                return
                
            # Read file into memory
            with open(filename, "rb") as f:
                file_bytes = f.read()
                
            # Create BytesIO object
            bio = BytesIO(file_bytes)
            bio.name = os.path.basename(filename)
            
            # Send the file
            await event.client.send_file(
                entity=event.chat_id,
                file=bio,
                caption=f"Subtitles ({lang}) for {safe_title}",
            )
            
            # Clean up the file and button
            safe_delete(filename)
            await event.delete()
            
        except Exception as e:
            await event.edit(f"Error: {str(e)}")
            
    except Exception as e:
        await event.edit(f"An unexpected error occurred: {str(e)}")

@events.register(events.CallbackQuery(pattern=r'ignore'))
async def ignore_callback(event):
    """Handle ignore callback for header buttons."""
    await event.answer("This is just a header, not a button.")

# Function to register all handlers
def register_yt_handlers(client: TelegramClient):
    """Register all YouTube download handlers with the Telethon client."""
    client.add_event_handler(yt_command)
    client.add_event_handler(yt_quality_button)
    client.add_event_handler(yt_audio_button)
    client.add_event_handler(yt_subs_callback)
    client.add_event_handler(ignore_callback)
    
    # Initialize user_data if not already available
    if not hasattr(client, 'user_data'):
        client.user_data = {}