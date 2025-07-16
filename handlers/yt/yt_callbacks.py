import os
import asyncio
from io import BytesIO
from pyrogram import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import active_downloads, download_locks, MAX_FILESIZE, download_cancellations
from .format_utils import extract_info
from .download_manager import download_video, download_audio_by_format, download_subtitles
from .upload_manager import upload_file_with_progress
from .file_utils import safe_delete

async def yt_quality_button(client: Client, callback_query):
    """Handle video quality selection callback."""
    try:
        await callback_query.answer()
        
        index = int(callback_query.data.split("_")[1])
        user_id = callback_query.from_user.id
        
        if user_id not in download_locks:
            download_locks[user_id] = asyncio.Lock()
        
        async with download_locks[user_id]:
            if user_id in active_downloads:
                await callback_query.message.edit(f"⚠️ You already have an active download in progress:\n\n{active_downloads[user_id]}\n\nPlease wait for it to complete before starting a new one.")
                return
            
            await callback_query.message.edit("🔍 Preparing download... fetching video details")
            
            user_data_key = f"yt_data_{callback_query.message.chat.id}_{callback_query.from_user.id}"
            yt_data = getattr(client, 'user_data', {}).get(user_data_key)
            
            if not yt_data:
                await callback_query.message.edit("Session expired. Please use /yt command again.")
                return
            
            video_url = yt_data['video_url']
            options = yt_data['options']
            best_audio = yt_data['best_audio']
            
            if index < 0 or index >= len(options):
                await callback_query.message.edit("Invalid selection.")
                return
            
            selected = options[index]
            resolution = selected['resolution']
            video_format_id = selected['format'].get('format_id')
            stream_type = selected['stream_type']
            
            await callback_query.message.edit(f"⏳ Fetching video metadata for {resolution} download...")
            
            try:
                info = await extract_info(video_url)
                video_title = info.get('title', 'Unknown video')
                active_downloads[user_id] = f"{video_title} [{resolution}]"
            except Exception as e:
                await callback_query.message.edit(f"❌ Error fetching video information: {str(e)}")
                return
            
            await callback_query.message.edit(f"⚙️ Initializing download for {resolution} quality...\n{video_title}")
            
            # Add cancel button
            cancel_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel Download", callback_data=f"cancel_{user_id}")]
            ])
            
            try:
                # Update message with cancel button - this will be preserved during progress updates
                await callback_query.message.edit(
                    f"⬇️ Starting download: {video_title} [{resolution}]",
                    reply_markup=cancel_button
                )
                
                filename, safe_title = await download_video(
                    video_url, 
                    video_format_id, 
                    best_audio, 
                    stream_type, 
                    resolution,
                    client,
                    callback_query.message.chat.id,
                    callback_query.message.id,
                    user_id,
                    cancel_button  # Pass the cancel button to download_video
                )
                
                if os.path.exists(filename):
                    file_size = os.path.getsize(filename)
                    if file_size > MAX_FILESIZE:
                        await callback_query.message.edit(f"Error: File size ({file_size/(1024*1024):.1f} MB) exceeds Telegram's limit of 2 GB.")
                        safe_delete(filename)
                        return
                else:
                    await callback_query.message.edit("Error: Downloaded file not found.")
                    return
                
                await upload_file_with_progress(
                    client,
                    callback_query.message.chat.id,
                    callback_query.message.id,
                    filename,
                    f"{safe_title} [{resolution}]",
                    yt_data.get('original_msg_id')
                )
                
                safe_delete(filename)
                
            except Exception as e:
                if "cancelled" in str(e).lower():
                    await callback_query.message.edit("❌ Download cancelled by user.")
                else:
                    await callback_query.message.edit(f"Error: {str(e)}")
            finally:
                if user_id in active_downloads:
                    del active_downloads[user_id]
                # Clean up cancellation state
                download_cancellations.pop(user_id, None)
            
    except Exception as e:
        if 'user_id' in locals() and user_id in active_downloads:
            del active_downloads[user_id]
        download_cancellations.pop(user_id, None)
        await callback_query.message.edit(f"An unexpected error occurred: {str(e)}")

async def yt_audio_button(client: Client, callback_query):
    """Handle audio quality selection callback."""
    try:
        await callback_query.answer()
        
        index = int(callback_query.data.split("_")[2])
        user_id = callback_query.from_user.id
        
        if user_id not in download_locks:
            download_locks[user_id] = asyncio.Lock()
        
        async with download_locks[user_id]:
            if user_id in active_downloads:
                await callback_query.message.edit(f"⚠️ You already have an active download in progress:\n\n{active_downloads[user_id]}\n\nPlease wait for it to complete before starting a new one.")
                return
            
            await callback_query.message.edit("🔍 Preparing audio download...")
            
            audio_key = f"yt_audio_{callback_query.message.chat.id}_{callback_query.from_user.id}"
            audio_options = getattr(client, 'user_data', {}).get(audio_key)
            
            if not audio_options or index < 0 or index >= len(audio_options):
                await callback_query.message.edit("Session expired or invalid selection. Please use /yt command again.")
                return
            
            selected = audio_options[index]
            
            data_key = f"yt_data_{callback_query.message.chat.id}_{callback_query.from_user.id}"
            main_data = getattr(client, 'user_data', {}).get(data_key, {})
            video_url = main_data.get("video_url")
            original_msg_id = main_data.get("original_msg_id")
            
            if not video_url:
                await callback_query.message.edit("Session expired. Please use /yt command again.")
                return
            
            info = await extract_info(video_url)
            audio_title = info.get('title', 'Unknown audio')
            active_downloads[user_id] = f"{audio_title} - {selected['abr']} kbps (audio)"
            
            audio_format_id = selected["format"].get("format_id")
            quality_str = f"{selected['abr']}kbps"
            
            await callback_query.message.edit(f"⚙️ Initializing audio download: {selected['abr']} kbps\n{audio_title}")
            
            # Add cancel button
            cancel_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel Download", callback_data=f"cancel_{user_id}")]
            ])
            
            try:
                # Update message with cancel button - this will be preserved during progress updates
                await callback_query.message.edit(
                    f"⬇️ Starting download: {audio_title} [{selected['abr']} kbps]",
                    reply_markup=cancel_button
                )
                
                filename, safe_title = await download_audio_by_format(
                    video_url, 
                    audio_format_id, 
                    quality_str, 
                    client, 
                    callback_query.message.chat.id, 
                    callback_query.message.id,
                    user_id,
                    cancel_button  # Pass the cancel button to download_audio_by_format
                )
                
                if not os.path.exists(filename):
                    await callback_query.message.edit("Error: Downloaded file not found.")
                    return
                    
                file_size = os.path.getsize(filename)
                if file_size > MAX_FILESIZE:
                    await callback_query.message.edit(f"Error: File size ({file_size/(1024*1024):.1f} MB) exceeds Telegram's limit.")
                    safe_delete(filename)
                    return
                    
                await upload_file_with_progress(
                    client,
                    callback_query.message.chat.id,
                    callback_query.message.id,
                    filename,
                    f"{safe_title} - {selected['abr']} kbps",
                    original_msg_id
                )
                
                safe_delete(filename)
                
            except Exception as e:
                if "cancelled" in str(e).lower():
                    await callback_query.message.edit("❌ Download cancelled by user.")
                else:
                    await callback_query.message.edit(f"Error: {str(e)}")
            finally:
                if user_id in active_downloads:
                    del active_downloads[user_id]
                # Clean up cancellation state
                download_cancellations.pop(user_id, None)
            
    except Exception as e:
        if 'user_id' in locals() and user_id in active_downloads:
            del active_downloads[user_id]
        download_cancellations.pop(user_id, None)
        await callback_query.message.edit(f"An unexpected error occurred: {str(e)}")

async def yt_subs_callback(client: Client, callback_query):
    """Handle subtitle language selection callback."""
    try:
        await callback_query.answer()
        
        lang = callback_query.data.split("_", 1)[1]
        user_id = callback_query.from_user.id
        
        subs_key = f"subs_data_{callback_query.message.chat.id}_{callback_query.from_user.id}"
        subs_data = getattr(client, 'user_data', {}).get(subs_key)
        
        if not subs_data:
            await callback_query.message.edit("Session expired. Please use /yt command with subs again.")
            return
        
        video_url = subs_data['video_url']
        safe_title = subs_data['safe_title']
        original_msg_id = subs_data.get('original_msg_id')
        
        await callback_query.message.edit(f"Downloading subtitles for language: {lang}...")
        
        try:
            filename = await download_subtitles(video_url, lang, safe_title, user_id)
            
            if not filename or not os.path.exists(filename):
                await callback_query.message.edit(f"Error: Subtitles for {lang} not available or could not be downloaded.")
                return
            
            file_size = os.path.getsize(filename)
            if file_size == 0:
                await callback_query.message.edit(f"Error: Downloaded subtitle file is empty.")
                safe_delete(filename)
                return
            
            with open(filename, "rb") as f:
                file_bytes = f.read()
                
            bio = BytesIO(file_bytes)
            bio.name = os.path.basename(filename)
            
            await client.send_document(
                chat_id=callback_query.message.chat.id,
                document=bio,
                caption=f"Subtitles ({lang}) for {safe_title}",
                reply_to_message_id=original_msg_id,
            )
            
            safe_delete(filename)
            await callback_query.message.delete()
            
        except Exception as e:
            await callback_query.message.edit(f"Error: {str(e)}")
            
    except Exception as e:
        await callback_query.message.edit(f"An unexpected error occurred: {str(e)}")

async def ignore_callback(client: Client, callback_query):
    """Handle ignore callback for header buttons."""
    await callback_query.answer("This is just a header, not a button.")

async def cancel_download_callback(client: Client, callback_query):
    """Handle download cancellation callback."""
    try:
        await callback_query.answer("Cancelling download...")
        
        # Extract user_id from callback data
        user_id = int(callback_query.data.split("_")[1])
        requesting_user = callback_query.from_user.id
        
        # Only allow the user who started the download to cancel it
        if user_id != requesting_user:
            await callback_query.answer("❌ You can only cancel your own downloads.", show_alert=True)
            return
        
        # Mark download for cancellation
        download_cancellations[user_id] = True
        
        # Update the message to show cancellation is in progress
        await callback_query.message.edit("⏳ Cancelling download, please wait...")
        
    except Exception as e:
        await callback_query.message.edit(f"Error cancelling download: {str(e)}")
