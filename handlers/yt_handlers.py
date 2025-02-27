import os
import re
import glob
import asyncio
import yt_dlp
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Maximum download filesize limit (2GB in bytes)
MAX_FILESIZE = 2147483648

def sanitize_filename(filename: str) -> str:
    """
    Remove characters not allowed in Windows filenames.
    Removes: < > : " / \ | ? * and fullwidth colon (：).
    Truncates to 100 characters if necessary and trims trailing spaces/dots.
    """
    sanitized = re.sub(r'[<>:"/\\|?*\uFF1A]', '', filename)
    sanitized = sanitized.strip().rstrip('.')
    return sanitized[:100] if len(sanitized) > 100 else sanitized

def safe_delete(filepath: str):
    """Delete the file if it exists."""
    if os.path.exists(filepath):
        os.remove(filepath)
    else:
        print(f"File not found for deletion: {filepath}")

def get_best_audio(info):
    """Return the best audio format (with known filesize) based on largest filesize."""
    audio_formats = [
        fmt for fmt in info.get('formats', [])
        if fmt.get('vcodec') == 'none' and (fmt.get('filesize') or fmt.get('filesize_approx'))
    ]
    return max(audio_formats, key=lambda f: f.get('filesize') or f.get('filesize_approx')) if audio_formats else None

def get_resolution(fmt):
    """Return a resolution string for a format."""
    if fmt.get('resolution'):
        return fmt['resolution']
    elif fmt.get('height'):
        return f"{fmt['height']}p"
    else:
        return "N/A"

def get_size(fmt):
    """Return filesize (exact or approximate) for a format."""
    return fmt.get('filesize') or fmt.get('filesize_approx')

def list_video_options(url):
    """
    Extract video info using yt-dlp and build a list of candidate MP4 formats.
    For adaptive streams, total size = video + best audio.
    Group options by resolution (keeping the one with the larger total size).
    Returns (info, video_options, best_audio).
    """
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
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
            total_size = video_size + audio_size if audio_size is not None else None
        candidates.append({
            'format': fmt,
            'resolution': resolution,
            'stream_type': stream_type,
            'video_size': video_size,
            'total_size': total_size,
        })
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
    video_options.sort(key=lambda c: c['format'].get('height') or 0)
    return info, video_options, best_audio

def list_audio_options(url):
    """
    Extract audio-only formats from the video info.
    Only considers formats where 'vcodec' == 'none', a filesize is known,
    and an audio bitrate ('abr') is provided.
    Duplicate options (by the same abr) are removed.
    Returns a list of dictionaries with keys: 'format', 'abr', 'filesize'.
    """
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
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

def download_video(url, video_format_id, best_audio, stream_type, resolution):
    """
    Download the YouTube video using yt-dlp.
    For adaptive streams (video-only) with best_audio available, merges audio.
    Saves the file in the "downloads" folder using a Windows-safe filename that includes the resolution.
    Returns a tuple (final_filename, safe_title).
    """
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
    safe_title = sanitize_filename(info.get("title", "video"))
    expected_filename = os.path.join("downloads", f"{safe_title} - {resolution}.mp4")
    if stream_type == "Adaptive" and best_audio:
        fmt_str = f"{video_format_id}+{best_audio.get('format_id')}"
    else:
        fmt_str = video_format_id
    outtmpl = expected_filename
    ydl_opts = {
        'format': fmt_str,
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'windowsfilenames': True,
        'outtmpl': outtmpl,
        'max_filesize': MAX_FILESIZE,
        'cookiefile': 'cookies.txt',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)
    return expected_filename, safe_title

def download_audio_by_format(url, audio_format_id, quality_str):
    """
    Download the audio using the specified format and convert it to MP3.
    The output template uses a quality label (e.g. "249kbps") so that the final file
    is named: <sanitized_title>.<quality_str>.mp3 (only one .mp3 appended).
    Returns a tuple (final_filename, safe_title).
    """
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
    safe_title = sanitize_filename(info.get("title", "audio"))
    expected_template = os.path.join("downloads", f"{safe_title}.{quality_str}.%(ext)s")
    ydl_opts = {
        'format': audio_format_id,
        'restrictfilenames': True,
        'windowsfilenames': True,
        'outtmpl': expected_template,
        'max_filesize': MAX_FILESIZE,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'cookiefile': 'cookies.txt',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    final_filename = os.path.join("downloads", f"{safe_title}.{quality_str}.mp3")
    return final_filename, safe_title

def download_audio_mp3(url):
    """
    Download the best available audio (converted to MP3) using yt-dlp.
    This function is kept for backward compatibility.
    """
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
    safe_title = sanitize_filename(info.get("title", "audio"))
    expected_filename = os.path.join("downloads", f"{safe_title}.mp3")
    outtmpl = expected_filename
    ydl_opts = {
        'format': 'bestaudio',
        'restrictfilenames': True,
        'windowsfilenames': True,
        'outtmpl': outtmpl,
        'max_filesize': MAX_FILESIZE,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'cookiefile': 'cookies.txt',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)
    return expected_filename, safe_title

def download_subtitles(url, lang, safe_title):
    """
    Download subtitles in the specified language for the given video URL.
    Uses auto subtitles if available.
    For English, applies a regex filter ("en.*") via yt-dlp options.
    Saves the file in the "downloads" folder with a sanitized title.
    Returns the full path of the downloaded subtitle file.
    """
    outtmpl = os.path.join("downloads", safe_title)
    sub_lang = "en.*" if lang.lower().startswith("en") else lang
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': [sub_lang],
        'subtitlesformat': 'srt',
        'outtmpl': outtmpl,
        'quiet': True,
        'cookiefile': 'cookies.txt',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    pattern_lang = "en" if lang.lower().startswith("en") else lang
    pattern = os.path.join("downloads", f"{safe_title}.{pattern_lang}.*")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    else:
        return None

async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /yt command handler.
    Usage:
      /yt <video URL>
      /yt subs <video URL>
      /yt <video URL> subs
    For YouTube:
      - If "subs" is included, fetch subtitle info and present buttons for available subtitle tracks.
        (Only tracks not containing "live_chat" are included.)
      - Otherwise, fetch video info and show inline buttons for video quality options and audio options.
    For non-YouTube, downloads the best-quality video directly.
    """
    if not context.args:
        await update.message.reply_text("Usage: /yt <video URL> [subs]")
        return

    subs_requested = False
    video_url = None
    for arg in context.args:
        if arg.lower() == "subs":
            subs_requested = True
        elif arg.startswith("http"):
            video_url = arg

    if not video_url:
        await update.message.reply_text("No valid video URL provided.")
        return

    if subs_requested:
        fetching_subs_message = await update.message.reply_text("Fetching subtitle info, please wait...")
        info = await asyncio.to_thread(lambda: yt_dlp.YoutubeDL({}).extract_info(video_url, download=False))
        safe_title = sanitize_filename(info.get("title", "subtitle"))
        # Build a union of manually provided subtitles and auto-generated captions,
        # filtering out any track that includes "live_chat"
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
            await fetching_subs_message.edit_text("No subtitles available for this video.")
            return

        keyboard = []
        for lang in subs_data.keys():
            button_text = lang
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"subs_{lang}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['yt_subtitles_data'] = {
            'video_url': video_url,
            'safe_title': safe_title,
        }
        await fetching_subs_message.edit_text("Choose subtitle language:", reply_markup=reply_markup)
        return

    # For video and audio downloads:
    fetching_vid_message = await update.message.reply_text("Fetching video info, please wait...")
    info, video_options, best_audio = await asyncio.to_thread(list_video_options, video_url)
    context.user_data['yt_data'] = {
        'video_url': video_url,
        'options': video_options,
        'best_audio': best_audio,
    }
    keyboard = []
    keyboard.append([InlineKeyboardButton("Video Options:", callback_data="ignore")])
    for i, option in enumerate(video_options):
        resolution = option['resolution']
        stream_type = option['stream_type']
        size = option['total_size']
        size_str = f"{size/(1024*1024):.2f} MB" if size else "N/A"
        button_text = f"{resolution} ({stream_type}, {size_str})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"yt_{i}")])
    audio_options = await asyncio.to_thread(list_audio_options, video_url)
    if audio_options:
        keyboard.append([InlineKeyboardButton("Audio Options:", callback_data="ignore")])
        for i, option in enumerate(audio_options):
            abr = option["abr"]
            size = option["filesize"]
            size_str = f"{size/(1024*1024):.2f} MB"
            button_text = f"{abr} kbps ({size_str})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"yt_audio_{i}")])
        context.user_data['yt_audio'] = audio_options

    reply_markup = InlineKeyboardMarkup(keyboard)
    await fetching_vid_message.edit_text("Choose video quality or audio (MP3):", reply_markup=reply_markup)

async def yt_quality_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    CallbackQuery handler for video quality buttons.
    Downloads the selected video and sends it as a video, then deletes the file.
    """
    query = update.callback_query
    await query.answer()
    try:
        index = int(query.data.split("_")[1])
    except Exception:
        await query.edit_message_text("Invalid selection.")
        return
    yt_data = context.user_data.get('yt_data')
    if not yt_data:
        await query.edit_message_text("No video data found. Please use /yt command again.")
        return
    video_url = yt_data['video_url']
    options = yt_data['options']
    best_audio = yt_data['best_audio']
    if index < 0 or index >= len(options):
        await query.edit_message_text("Invalid selection.")
        return
    selected = options[index]
    resolution = selected['resolution']
    video_format_id = selected['format'].get('format_id')
    stream_type = selected['stream_type']
    await query.edit_message_text(f"Downloading video at {resolution}...")
    filename, safe_title = await asyncio.to_thread(download_video, video_url, video_format_id, best_audio, stream_type, resolution)
    try:
        with open(filename, "rb") as f:
            await context.bot.send_video(chat_id=update.effective_chat.id,
                                           video=f,
                                           caption=safe_title,
                                           reply_to_message_id=query.message.message_id)
    except Exception as e:
        await query.edit_message_text(f"Error uploading video: {e}")
    finally:
        safe_delete(filename)

async def yt_audio_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    CallbackQuery handler for audio quality buttons.
    Downloads the selected audio track (converted to MP3) and sends it as an audio file, then deletes the file.
    """
    query = update.callback_query
    await query.answer()
    try:
        index = int(query.data.split("_")[2])
    except Exception:
        await query.edit_message_text("Invalid audio selection.")
        return
    audio_options = context.user_data.get('yt_audio')
    if not audio_options or index < 0 or index >= len(audio_options):
        await query.edit_message_text("Invalid audio selection.")
        return
    selected = audio_options[index]
    video_url = context.user_data.get("yt_data", {}).get("video_url")
    if not video_url:
        await query.edit_message_text("Video URL not found.")
        return
    audio_format_id = selected["format"].get("format_id")
    quality_str = f"{selected['abr']}kbps"
    await query.edit_message_text(f"Downloading audio at {selected['abr']} kbps...")
    filename, safe_title = await asyncio.to_thread(download_audio_by_format, video_url, audio_format_id, quality_str)
    try:
        with open(filename, "rb") as f:
            file_data = f.read()
        bio = BytesIO(file_data)
        bio.name = os.path.basename(filename)
        await context.bot.send_audio(chat_id=update.effective_chat.id,
                                       audio=bio,
                                       caption=f"{safe_title} - {selected['abr']} kbps",
                                       reply_to_message_id=query.message.message_id)
    except Exception as e:
        await query.edit_message_text(f"Error sending audio: {e}")
    finally:
        safe_delete(filename)

async def yt_subs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    CallbackQuery handler for subtitle language buttons.
    Downloads the subtitle file, sends it as a document, then deletes the file.
    """
    query = update.callback_query
    await query.answer()
    try:
        lang = query.data.split("_", 1)[1]
    except Exception:
        await query.edit_message_text("Invalid subtitle selection.")
        return

    yt_data = context.user_data.get('yt_subtitles_data')
    if not yt_data:
        await query.edit_message_text("No subtitle data found. Please use /yt command with subs again.")
        return

    video_url = yt_data['video_url']
    safe_title = yt_data['safe_title']
    await query.edit_message_text(f"Downloading subtitles for language: {lang} ...")
    filename = await asyncio.to_thread(download_subtitles, video_url, lang, safe_title)
    if not filename or not os.path.exists(filename):
        await query.edit_message_text("Subtitle file not found. It may not be available in the requested format.")
        return

    try:
        with open(filename, "rb") as f:
            file_bytes = f.read()
        bio = BytesIO(file_bytes)
        bio.name = os.path.basename(filename)
        await context.bot.send_document(chat_id=update.effective_chat.id,
                                        document=bio,
                                        caption=f"Subtitles ({lang}) for {safe_title}",
                                        reply_to_message_id=query.message.message_id)
    except Exception as e:
        await query.edit_message_text(f"Error sending subtitles: {e}")
    finally:
        safe_delete(filename)
