import os
import glob
import asyncio
import yt_dlp
import time
import logging
import random
import socket
import http.client
from typing import Dict, Optional, Tuple
from .constants import MAX_FILESIZE, MAX_RETRIES, INITIAL_RETRY_DELAY, MAX_RETRY_DELAY, download_cancellations
from .format_utils import add_cookies_to_opts, extract_info, get_size
from .file_utils import sanitize_filename, get_user_downloads_dir, safe_delete
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

async def download_video(url: str, video_format_id: str, best_audio: Optional[Dict], 
                        stream_type: str, resolution: str, client, chat_id, message_id, user_id=None, cancel_markup=None) -> Tuple[str, str]:
    """Download video at specified quality with progress updates."""
    if user_id is None:
        user_id = chat_id if chat_id > 0 else None
    
    # Clear any previous cancellation state
    download_cancellations.pop(user_id, None)
    
    tracker = ProgressTracker(
        client, 
        chat_id, 
        message_id, 
        f"Preparing {resolution} download...", 
        cancel_markup  # Pass the cancel button markup
    )
    await tracker.update_progress(0, 1, 0, None, force=True)
    
    info = await extract_info(url)
    safe_title = sanitize_filename(info.get("title", "video"))
    
    # Create user directory and set filename
    user_downloads_dir = get_user_downloads_dir(user_id)
    expected_filename = os.path.join(user_downloads_dir, f"{safe_title} - {resolution}.mp4")
    
    # Update the progress message to show we're now initializing the download
    tracker.description = f"Initializing download for: {safe_title} [{resolution}]"
    await tracker.update_progress(0, 1, 0, None, force=True)
    
    # Initialize progress state with simpler tracking
    progress = {
        "video_bytes": 0,      # Video bytes downloaded
        "video_total": 0,      # Total video bytes
        "audio_bytes": 0,      # Audio bytes downloaded
        "audio_total": 0,      # Total audio bytes
        "merged_bytes": 0,     # Post-processing bytes
        "current_stage": "video",  # Current stage: 'video', 'audio', 'merging'
        "speed": 0,            # Current download speed
        "eta": None,           # Estimated time to completion
        "last_update": 0,      # Last update time
        "filename": "",        # Current file being downloaded
        "event": asyncio.Event(), # Event for signaling progress updates
        "finished": False      # Whether download is complete
    }
    
    # Estimate total size once at the beginning
    total_size = 0
    video_size = 0
    audio_size = 0
    
    if "adaptive" in stream_type.lower():
        # For adaptive formats, we need to know both video and audio size
        if best_audio:
            audio_size = get_size(best_audio) or 0
        
        # Try to get video size from formats
        formats = info.get('formats', [])
        for fmt in formats:
            if fmt.get('format_id') == video_format_id:
                video_size = get_size(fmt) or 0
                break
        
        total_size = video_size + audio_size
        progress["video_total"] = video_size
        progress["audio_total"] = audio_size
    
    # Send initial progress message
    await tracker.update_progress(0, total_size or 1, 0, None, force=True)
    
    # Define progress hook for yt-dlp
    def progress_hook(d):
        # Check for cancellation at each progress update
        if user_id in download_cancellations:
            # Use a custom exception instead of KeyboardInterrupt to avoid asyncio issues
            raise Exception("DOWNLOAD_CANCELLED_BY_USER")
            
        if d['status'] == 'downloading':
            # Get download information
            bytes_downloaded = d.get('downloaded_bytes', 0)
            bytes_total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta')
            filename = d.get('info_dict', {}).get('_filename', '')
            
            # Detect stage change by filename
            if filename != progress["filename"]:
                progress["filename"] = filename
                
                # If we have some video downloaded and now filename changed, we're in audio stage
                if progress["video_bytes"] > 0 and "adaptive" in stream_type.lower():
                    progress["current_stage"] = "audio"
                    # Lock in video bytes for continuous progress calculation
                    if progress["video_total"] > 0:
                        progress["video_bytes"] = progress["video_total"]
            
            # Update appropriate stage metrics
            if progress["current_stage"] == "video":
                progress["video_bytes"] = bytes_downloaded
                if bytes_total > 0 and progress["video_total"] == 0:
                    progress["video_total"] = bytes_total
            elif progress["current_stage"] == "audio":
                progress["audio_bytes"] = bytes_downloaded
                if bytes_total > 0 and progress["audio_total"] == 0:
                    progress["audio_total"] = bytes_total
            
            # Update speed and ETA
            progress["speed"] = speed
            progress["eta"] = eta
            
            # Signal for progress update
            progress["last_update"] = time.time()
            progress["event"].set()
            
        elif d['status'] == 'finished':
            # If we finished downloading but we're not done yet, we're changing stages
            if progress["current_stage"] == "video" and "adaptive" in stream_type.lower():
                progress["current_stage"] = "audio"
                # Lock in the video progress
                if progress["video_total"] > 0:
                    progress["video_bytes"] = progress["video_total"]
            else:
                # Both video and audio are done, now in processing stage
                progress["current_stage"] = "merging"
            
            progress["event"].set()
            
        elif d['status'] == 'error':
            progress["finished"] = True
            progress["event"].set()
    
    # Task to update progress UI
    async def update_progress_ui():
        last_update_time = 0
        min_update_interval = 3  # Minimum seconds between updates
        
        while not progress["finished"]:
            try:
                # Check for cancellation
                if user_id in download_cancellations:
                    tracker.description = f"Cancelling download: {safe_title} [{resolution}]"
                    await tracker.update_progress(0, 1, 0, 0, force=True)
                    progress["finished"] = True
                    break
                
                # Wait for event or timeout
                try:
                    await asyncio.wait_for(progress["event"].wait(), 5)
                    progress["event"].clear()
                except asyncio.TimeoutError:
                    # No updates for 5 seconds, check if we need to send a periodic update
                    pass
                
                # Calculate current progress based on stage
                current_time = time.time()
                if current_time - last_update_time < min_update_interval:
                    continue  # Too soon for another update
                
                # Calculate overall progress based on stage
                total_bytes = max(1, progress["video_total"] + progress["audio_total"])
                downloaded_bytes = 0
                
                if "adaptive" in stream_type.lower():
                    # For adaptive format, combine video and audio progress
                    if progress["current_stage"] == "video":
                        downloaded_bytes = progress["video_bytes"]
                        # Update description to show stage
                        tracker.description = f"Downloading {resolution} video [Video]"
                    elif progress["current_stage"] == "audio":
                        # Video is complete, add audio progress
                        downloaded_bytes = progress["video_total"] + progress["audio_bytes"]
                        tracker.description = f"Downloading {resolution} video [Audio]"
                    elif progress["current_stage"] == "merging":
                        # Both downloads complete, show processing
                        downloaded_bytes = total_bytes * 0.95  # 95% complete during processing
                        tracker.description = f"Processing {resolution} video [Merging]"
                else:
                    # For progressive format, simpler calculation
                    downloaded_bytes = progress["video_bytes"]
                    tracker.description = f"Downloading {resolution} video"
                
                # Get current speed and ETA
                speed = progress["speed"]
                eta = progress["eta"]
                
                # Update the progress UI
                await tracker.update_progress(downloaded_bytes, total_bytes, speed, eta)
                last_update_time = current_time
                
            except Exception as e:
                logger.error(f"Error in progress UI updater: {e}")
                await asyncio.sleep(5)  # Wait before trying again
    
    # Start the UI updater task
    updater_task = asyncio.create_task(update_progress_ui())
    
    # Check if this is an Instagram URL to determine encoding strategy
    is_instagram = 'instagram.com' in url.lower() or 'instagr.am' in url.lower()
    
    # Configure yt-dlp options with optimized encoding
    fmt_str = f"{video_format_id}+bestaudio/best" if "adaptive" in stream_type.lower() else video_format_id
    
    if is_instagram:
        # For Instagram videos, use minimal re-encoding for WhatsApp compatibility
        postprocessor_args = {
            'ffmpeg': [
                '-c:v', 'libx264',      # Re-encode video with H.264
                '-preset', 'ultrafast', # Fastest encoding (less compression but faster)
                '-crf', '28',           # Higher CRF for smaller files (was 23)
                '-profile:v', 'main',   # Main profile instead of baseline
                '-level', '4.0',        # Higher level for better compression
                '-c:a', 'copy',         # Copy audio if already AAC
                '-movflags', '+faststart',
                '-pix_fmt', 'yuv420p',
                '-maxrate', '2M',       # Limit bitrate to 2Mbps
                '-bufsize', '4M'        # Buffer size
            ]
        }
    else:
        # For other videos, prioritize stream copying
        postprocessor_args = {
            'ffmpeg': [
                '-c:v', 'copy',         # Copy video stream
                '-c:a', 'aac',          # Convert audio to AAC only if needed
                '-b:a', '128k',         # Limit audio bitrate
                '-avoid_negative_ts', 'make_zero',
                '-movflags', '+faststart'
            ]
        }
    
    ydl_opts = add_cookies_to_opts({
        'format': fmt_str,
        'merge_output_format': 'mp4',
        'windowsfilenames': True,
        'outtmpl': expected_filename,
        'max_filesize': MAX_FILESIZE,
        'postprocessor_args': postprocessor_args,
        'prefer_ffmpeg': True,
        'keepvideo': False,
        'progress_hooks': [progress_hook],
        'verbose': False,
    })
    
    try:
        # Perform the actual download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await download_with_retry(ydl, url)
        
        # Check if cancelled during download
        if user_id in download_cancellations:
            raise Exception("DOWNLOAD_CANCELLED_BY_USER")
        
        # Mark as complete
        progress["finished"] = True
        progress["event"].set()
        
        # Show complete status
        tracker.description = f"Download complete: {safe_title} [{resolution}]"
        if os.path.exists(expected_filename):
            file_size = os.path.getsize(expected_filename)
            await tracker.update_progress(file_size, file_size, 0, 0, force=True)
        
        # Clean up updater task
        if not updater_task.done():
            updater_task.cancel()
            try:
                await updater_task
            except asyncio.CancelledError:
                pass
        
        # Check if file exists or find it if needed
        if not os.path.exists(expected_filename):
            pattern = os.path.join(user_downloads_dir, f"{safe_title}*.mp4")
            matches = glob.glob(pattern)
            if matches:
                expected_filename = matches[0]
            else:
                raise ValueError("Downloaded file not found")
    
    except Exception as e:
        # Handle errors and cancellation
        progress["finished"] = True
        progress["event"].set()
        
        # Cancel the updater
        if not updater_task.done():
            updater_task.cancel()
            try:
                await updater_task
            except asyncio.CancelledError:
                pass
        
        # Check if this was a cancellation
        if "DOWNLOAD_CANCELLED_BY_USER" in str(e) or user_id in download_cancellations:
            # Clean up any partial files
            try:
                if os.path.exists(expected_filename):
                    safe_delete(expected_filename)
                
                # Also clean up any temp files in the user directory
                user_downloads_dir = get_user_downloads_dir(user_id)
                temp_patterns = [
                    os.path.join(user_downloads_dir, f"*{safe_title}*.part"),
                    os.path.join(user_downloads_dir, f"*{safe_title}*.tmp"),
                    os.path.join(user_downloads_dir, f"*{safe_title}*.download"),
                    os.path.join(user_downloads_dir, f"*.f{video_format_id}.*"),
                ]
                
                for pattern in temp_patterns:
                    for temp_file in glob.glob(pattern):
                        safe_delete(temp_file)
                        
            except Exception as cleanup_error:
                logger.error(f"Error during file cleanup: {cleanup_error}")
            
            # Update UI with cancellation message
            tracker.description = f"Download cancelled: {safe_title} [{resolution}]"
            await tracker.update_progress(0, 1, 0, 0, force=True)
            
            raise ValueError("Download cancelled by user")
        else:
            # Update UI with error
            tracker.description = f"Download failed: {str(e)}"
            await tracker.update_progress(0, 1, 0, 0, force=True)
            
            # Re-raise the error
            raise ValueError(f"Error downloading video: {str(e)}")
        
    return expected_filename, safe_title

async def download_with_retry(ydl, url, retries=MAX_RETRIES, initial_delay=INITIAL_RETRY_DELAY):
    """Download with retry logic for handling network errors."""
    delay = initial_delay
    last_error = None
    
    for attempt in range(retries + 1):
        try:
            if isinstance(url, list):
                return await asyncio.to_thread(ydl.download, url)
            else:
                return await asyncio.to_thread(ydl.extract_info, url, download=True)
        except Exception as e:
            # Check if this is a cancellation
            if "DOWNLOAD_CANCELLED_BY_USER" in str(e):
                raise e  # Re-raise cancellation immediately
                
            # Handle network errors with retry
            if isinstance(e, (ConnectionResetError, ConnectionError, socket.error, http.client.IncompleteRead,
                            yt_dlp.utils.DownloadError, OSError)):
                last_error = e
                if attempt < retries:
                    jitter = random.uniform(0.1, 0.3) * delay
                    retry_delay = delay + jitter
                    logger.warning(f"Download attempt {attempt+1}/{retries+1} failed: {str(e)}. Retrying in {retry_delay:.2f}s...")
                    
                    await asyncio.sleep(retry_delay)
                    delay = min(delay * 2, MAX_RETRY_DELAY)
                else:
                    raise ValueError(f"Download failed after {retries+1} attempts: {str(last_error)}")
            else:
                # For other errors, don't retry
                raise ValueError(f"Unexpected error during download: {str(e)}")

async def download_audio_by_format(url: str, audio_format_id: str, quality_str: str, client, chat_id, message_id, user_id=None, cancel_markup=None) -> Tuple[str, str]:
    """Download audio at specified quality with progress updates."""
    if user_id is None:
        user_id = chat_id if chat_id > 0 else None
        logger.warning(f"No specific user_id provided for audio download. Using fallback: {user_id}")
    
    # Clear any previous cancellation state
    download_cancellations.pop(user_id, None)
    
    info = await extract_info(url)
    safe_title = sanitize_filename(info.get("title", "audio"))
    
    # Use user-specific directory
    user_downloads_dir = get_user_downloads_dir(user_id)
    expected_template = os.path.join(user_downloads_dir, f"{safe_title}.{quality_str}.%(ext)s")
    expected_filename = os.path.join(user_downloads_dir, f"{safe_title}.{quality_str}.mp3")
    
    tracker = ProgressTracker(
        client, 
        chat_id, 
        message_id, 
        f"Downloading audio at {quality_str}...", 
        cancel_markup  # Pass the cancel button markup
    )
    
    # Create a shared progress state
    progress_state = {
        "downloaded": 0,
        "total": 0,
        "speed": 0,
        "eta": None,
        "last_update_time": 0,
        "update_required": asyncio.Event(),
        "finished": False,
        "last_update_attempt": 0,     
        "min_update_interval": 5.0,   # Increased from 2.0 to 5.0 seconds
        "min_bytes_change": 3 * 1024 * 1024,  # 3MB minimum bytes change
        "last_bytes": 0,
        "last_percent": 0,
    }
    
    # Send initial progress message
    try:
        await tracker.update_progress(0, 1, 0, None)
    except Exception as e:
        logger.error(f"Failed to send initial progress message: {e}")
        # Continue anyway - download is more important than progress updates
    
    def progress_hook(d):
        """Progress hook for yt-dlp."""
        # Check for cancellation
        if user_id in download_cancellations:
            raise Exception("DOWNLOAD_CANCELLED_BY_USER")
            
        if d['status'] == 'downloading':
            current_time = time.time()
            progress_state["downloaded"] = d.get('downloaded_bytes', 0)
            progress_state["total"] = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            progress_state["speed"] = d.get('speed')
            progress_state["eta"] = d.get('eta')
            
            # More conservative update strategy with added bytes condition
            time_condition = current_time - progress_state["last_update_time"] >= progress_state["min_update_interval"]
            progress_condition = False
            bytes_condition = False
            
            if progress_state["total"] > 0:
                last_percent = progress_state.get("last_percent", 0)
                curr_percent = (progress_state["downloaded"] / progress_state["total"]) * 100
                progress_condition = abs(curr_percent - last_percent) >= 1  # 1% change threshold
                progress_state["last_percent"] = curr_percent
                
            # Add check for minimum bytes downloaded
            last_bytes = progress_state.get("last_bytes", 0)
            bytes_condition = abs(progress_state["downloaded"] - last_bytes) >= progress_state["min_bytes_change"]
            
            if time_condition and (progress_condition or bytes_condition or 
                                  progress_state["downloaded"] == 0 or 
                                  progress_state["downloaded"] == progress_state["total"]):
                progress_state["last_update_time"] = current_time
                progress_state["last_bytes"] = progress_state["downloaded"]
                progress_state["update_required"].set()
        elif d['status'] == 'finished':
            progress_state["finished"] = True
            progress_state["update_required"].set()
    
    # Task to update progress display
    async def progress_updater():
        last_percent = 0
        retry_interval = 3.0  # Start with 3 second retry (increased from 1)
        
        while not progress_state["finished"]:
            try:
                # Check for cancellation
                if user_id in download_cancellations:
                    tracker.description = f"Cancelling audio download: {quality_str}"
                    await tracker.update_progress(0, 1, 0, 0, force=True)
                    progress_state["finished"] = True
                    break
                
                # Wait for event or timeout after retry_interval seconds
                await asyncio.wait_for(progress_state["update_required"].wait(), retry_interval)
                progress_state["update_required"].clear()
                
                # If we're in a rate limit backoff, check if we should increase the retry interval
                if tracker.flood_wait_until > time.time():
                    # Calculate remaining flood wait time
                    remaining = tracker.flood_wait_until - time.time()
                    if remaining > 0:
                        # More conservative retry interval
                        retry_interval = min(remaining * 0.75, 15.0)  # No more than 15 seconds
                        logger.info(f"In flood wait period, adjusted retry interval to {retry_interval:.1f}s")
                        # Skip this update but keep the download going
                        continue
                
                # Send the update with more intelligent throttling
                current_time = time.time()
                current_percent = 0
                if progress_state["total"] > 0:
                    current_percent = (progress_state["downloaded"] / progress_state["total"]) * 100
                    
                # Only send update if there's been substantial change or it's been a while
                should_update = (current_time - tracker.last_update_time >= tracker.update_interval or 
                                abs(current_percent - last_percent) >= tracker.min_progress_change)
                
                if should_update:
                    await tracker.update_progress(
                        progress_state["downloaded"],
                        progress_state["total"],
                        progress_state["speed"],
                        progress_state["eta"]
                    )
                    last_percent = current_percent
                
                # Adjust retry interval based on download speed and remaining percentage
                if progress_state["speed"] and progress_state["speed"] > 0 and progress_state["total"] > 0:
                    percent_remaining = 100 - current_percent
                    # For fast downloads with little remaining, update more frequently
                    if progress_state["speed"] > 500000 and percent_remaining < 20:  # 500KB/s
                        retry_interval = 2.0
                    # For slow downloads or lots remaining, check less frequently
                    elif progress_state["speed"] < 100000 or percent_remaining > 80:  # 100KB/s
                        retry_interval = 8.0
                    else:
                        retry_interval = 4.0
                else:
                    # Default retry interval
                    retry_interval = 5.0
                    
            except asyncio.TimeoutError:
                # Only send periodic updates if significant time has passed
                if progress_state["total"] > 0 and progress_state["downloaded"] > 0:
                    current_time = time.time()
                    if current_time - tracker.last_update_time >= tracker.update_interval:
                        current_percent = (progress_state["downloaded"] / progress_state["total"]) * 100
                        if abs(current_percent - last_percent) >= 1:  # Only update if 1% change
                            await tracker.update_progress(
                                progress_state["downloaded"],
                                progress_state["total"],
                                progress_state["speed"],
                                progress_state["eta"]
                            )
                            last_percent = current_percent
            except Exception as e:
                logger.error(f"Error updating progress: {e}")
                retry_interval = min(retry_interval * 2.0, 20.0)  # More aggressive exponential backoff
    
    # Start the updater task
    updater_task = asyncio.create_task(progress_updater())
    
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
        'progress_hooks': [progress_hook],
        'verbose': False,
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
    })
    
    try:
        tracker.description = f"Downloading audio at {quality_str}..."
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Use our custom retry function instead of direct call
            await download_with_retry(ydl, [url])
        
        # Check if cancelled during download
        if user_id in download_cancellations:
            raise Exception("DOWNLOAD_CANCELLED_BY_USER")
        
        # Update with final progress (100%)
        if progress_state["total"] > 0:
            await tracker.update_progress(
                progress_state["total"],  # Set downloaded = total for 100%
                progress_state["total"],
                progress_state["speed"],
                0  # ETA is now 0
            )
        
        # Mark as finished and clean up the updater task
        progress_state["finished"] = True
        progress_state["update_required"].set()  # Wake up the updater one last time
        await asyncio.sleep(0.5)  # Give it time to process
        
        if not updater_task.done():
            updater_task.cancel()
            try:
                await updater_task
            except asyncio.CancelledError:
                pass
                
        if not os.path.exists(expected_filename):
            # Try to find the actual file if outtmpl didn't work as expected
            pattern = os.path.join(user_downloads_dir, f"{safe_title}*.mp3")
            matches = glob.glob(pattern)
            if matches:
                expected_filename = matches[0]
    except Exception as e:
        # Cancel the updater task in case of error
        progress_state["finished"] = True
        progress_state["update_required"].set()
        if not updater_task.done():
            updater_task.cancel()
            try:
                await updater_task
            except asyncio.CancelledError:
                pass
        
        # Check if this was a cancellation
        if "DOWNLOAD_CANCELLED_BY_USER" in str(e) or user_id in download_cancellations:
            # Clean up any partial files
            try:
                if os.path.exists(expected_filename):
                    safe_delete(expected_filename)
                
                # Clean up temp files
                user_downloads_dir = get_user_downloads_dir(user_id)
                temp_patterns = [
                    os.path.join(user_downloads_dir, f"*{safe_title}*.part"),
                    os.path.join(user_downloads_dir, f"*{safe_title}*.tmp"),
                    os.path.join(user_downloads_dir, f"*{safe_title}*.download"),
                    os.path.join(user_downloads_dir, f"*.f{audio_format_id}.*"),
                ]
                
                for pattern in temp_patterns:
                    for temp_file in glob.glob(pattern):
                        safe_delete(temp_file)
                        
            except Exception as cleanup_error:
                logger.error(f"Error during file cleanup: {cleanup_error}")
            
            # Update progress message with cancellation info
            try:
                tracker.description = "Audio download cancelled"
                await tracker.update_progress(0, 1, 0, 0)
            except:
                pass
                
            raise ValueError("Download cancelled by user")
        else:
            # Handle other errors
            error_msg = str(e)
            if "ConnectionReset" in error_msg or "10054" in error_msg:
                logger.error(f"Network connection was reset during audio download: {error_msg}")
                try:
                    tracker.description = "Audio download failed - connection reset"
                    await tracker.update_progress(0, 1, 0, 0)
                except:
                    pass
            
            raise ValueError(f"Error downloading audio: {str(e)}")
        
    return expected_filename, safe_title

async def download_subtitles(url: str, lang: str, safe_title: str, user_id: int) -> Optional[str]:
    """Download subtitles in specified language."""
    user_downloads_dir = get_user_downloads_dir(user_id)
    outtmpl = os.path.join(user_downloads_dir, safe_title)
    
    # Handle language formatting
    sub_lang = lang
    if "auto-generated" in lang:
        sub_lang = lang.split(" ")[0]
    
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
    pattern = os.path.join(user_downloads_dir, f"{safe_title}.{sub_lang}.*")
    matches = glob.glob(pattern)
    
    if not matches:
        pattern = os.path.join(user_downloads_dir, f"{safe_title}.*.{sub_lang}.*")
        matches = glob.glob(pattern)
        
    if matches:
        return matches[0]
    else:
        return None
    if matches:
        return matches[0]
    else:
        return None
