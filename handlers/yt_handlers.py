import os
import re
import glob
import asyncio
import yt_dlp
import time
import logging
import random
import socket
import http.client
from io import BytesIO
from telethon import TelegramClient, events, Button, errors
from typing import Dict, List, Optional, Any, Tuple

from utils.usage import save_usage

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_FILESIZE = 2147483648  # 2GB max file size for Telegram
COOKIES_FILE = 'cookies.txt'
DOWNLOADS_DIR = 'downloads'
MAX_RETRIES = 3  # Maximum number of retry attempts
INITIAL_RETRY_DELAY = 2  # Initial delay between retries in seconds
MAX_RETRY_DELAY = 10  # Maximum delay between retries in seconds

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

def format_bytes(byte_count):
    """Format bytes as human-readable file size."""
    if byte_count is None:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if byte_count < 1024.0:
            if unit == 'B':
                return f"{byte_count:.0f} {unit}"
            return f"{byte_count:.2f} {unit}"
        byte_count /= 1024.0
    return f"{byte_count:.2f} TB"

def format_speed(speed):
    """Format speed as human-readable."""
    if speed is None or speed <= 0:
        return "Unknown"
    return f"{format_bytes(speed)}/s"

def format_eta(seconds):
    """Format ETA in a human-readable format."""
    if seconds is None:
        return "Unknown"
    
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:.0f}h {mins:.0f}m {secs:.0f}s"
    elif mins > 0:
        return f"{mins:.0f}m {secs:.0f}s"
    else:
        return f"{secs:.0f}s"

class ProgressTracker:
    def __init__(self, client, chat_id, message_id, description):
        self.client = client
        self.chat_id = chat_id
        self.message_id = message_id
        self.description = description
        self.last_update_time = 0
        self.start_time = time.time()
        self.last_progress = 0
        self.last_total = 0
        self.update_interval = 15  # Increased from 10 to 15 seconds between updates
        self.min_progress_change = 1  # Minimum percentage change to trigger an update (changed from 20% to 1%)
        self.min_bytes_change = 3 * 1024 * 1024  # 3MB minimum change to trigger update
        self.tasks = []  # Track all progress update tasks
        self.flood_wait_until = 0  # Timestamp when flood wait expires
        self.consecutive_flood_waits = 0  # Count consecutive flood waits for backoff
        self.max_backoff = 60  # Maximum backoff in seconds (increased from 30)

    async def update_progress(self, current, total, speed=None, eta=None):
        """Update progress message if enough time has passed."""
        current_time = time.time()
        
        # If we're in a flood wait period, check if it's expired
        if self.flood_wait_until > current_time:
            # Skip this update as we're still in flood wait
            return
            
        progress_change = abs(current - self.last_progress) / (total or 1) * 100
        bytes_change = abs(current - self.last_progress)
        
        # Only update if:
        # 1. Significant time passed or
        # 2. Significant progress change (percentage) or
        # 3. Significant amount of bytes downloaded (3MB+) or
        # 4. Completed or
        # 5. First real progress update
        if (current_time - self.last_update_time >= self.update_interval or 
            progress_change >= self.min_progress_change or
            bytes_change >= self.min_bytes_change or
            (current == total and total > 0) or  
            (current > 0 and self.last_progress == 0)):
            
            self.last_update_time = current_time
            self.last_progress = current
            self.last_total = total
            
            # Calculate speed if not provided
            if speed is None and current > 0:
                elapsed = current_time - self.start_time
                if elapsed > 0:
                    speed = current / elapsed
            
            # Format the progress message
            if total > 0:
                percentage = current / total * 100
                progress_bar = self._get_progress_bar(percentage)
                speed_str = format_speed(speed) if speed else "Calculating..."
                eta_str = format_eta(eta) if eta is not None else "Calculating..."
                
                msg = (
                    f"{self.description}\n"
                    f"{progress_bar} {percentage:.1f}%\n"
                    f"{format_bytes(current)} / {format_bytes(total)}\n"
                    f"Speed: {speed_str} | ETA: {eta_str}"
                )
            else:
                speed_str = format_speed(speed) if speed else "Calculating..."
                msg = (
                    f"{self.description}\n"
                    f"Downloaded: {format_bytes(current)}\n"
                    f"Speed: {speed_str}"
                )
            
            try:
                await self.client.edit_message(self.chat_id, self.message_id, msg)
                # Reset consecutive flood waits on successful update
                self.consecutive_flood_waits = 0
            except errors.FloodWaitError as e:
                # Handle flood wait error
                wait_time = e.seconds
                logger.info(f"Flood wait detected: {wait_time}s. Download continues in background.")
                
                # Set the flood wait expiration time
                self.flood_wait_until = current_time + wait_time
                
                # Implement exponential backoff for consecutive flood waits
                self.consecutive_flood_waits += 1
                # Add additional backoff based on consecutive waits (max 30 seconds)
                self.flood_wait_until += min(self.consecutive_flood_waits * 5, self.max_backoff)
            except Exception as e:
                logger.error(f"Failed to update progress: {e}")
    
    def _get_progress_bar(self, percentage, length=20):
        """Generate a text-based progress bar."""
        filled_length = int(length * percentage / 100)
        bar = '█' * filled_length + '▒' * (length - filled_length)
        return f"[{bar}]"
    
    def schedule_update(self, current, total, speed=None, eta=None):
        """Schedule a progress update from a synchronous context."""
        # Create a task wrapper that catches exceptions
        async def task_wrapper():
            try:
                await self.update_progress(current, total, speed, eta)
            except Exception as e:
                logger.error(f"Error in progress update task: {e}")
        
        # Create a new task and track it
        task = asyncio.create_task(task_wrapper())
        self.tasks.append(task)
        
        # Add a callback to remove the task when done
        def cleanup_task(t):
            try:
                if t in self.tasks:
                    self.tasks.remove(t)
            except Exception as e:
                logger.error(f"Error cleaning up task: {e}")
        
        task.add_done_callback(cleanup_task)
    
    async def cleanup(self):
        """Wait for all pending tasks to complete."""
        if self.tasks:
            pending_tasks = [task for task in self.tasks if not task.done()]
            if pending_tasks:
                await asyncio.gather(*pending_tasks, return_exceptions=True)
            self.tasks.clear()

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
        except (ConnectionResetError, ConnectionError, socket.error, http.client.IncompleteRead,
                yt_dlp.utils.DownloadError, OSError) as e:
            last_error = e
            if attempt < retries:
                # Add some jitter to the delay to prevent synchronized retries
                jitter = random.uniform(0.1, 0.3) * delay
                retry_delay = delay + jitter
                logger.warning(f"Download attempt {attempt+1}/{retries+1} failed: {str(e)}. Retrying in {retry_delay:.2f}s...")
                
                # Update progress state with retry information if tracker is provided
                await asyncio.sleep(retry_delay)
                
                # Exponential backoff with cap
                delay = min(delay * 2, MAX_RETRY_DELAY)
            else:
                # Last attempt failed, re-raise the error
                raise ValueError(f"Download failed after {retries+1} attempts: {str(last_error)}")
        except Exception as e:
            # For other errors, don't retry
            raise ValueError(f"Unexpected error during download: {str(e)}")

async def download_video(url: str, video_format_id: str, best_audio: Optional[Dict[str, Any]], 
                        stream_type: str, resolution: str, client, chat_id, message_id) -> Tuple[str, str]:
    """Download video at specified quality with progress updates."""
    info = await extract_info(url)
    safe_title = sanitize_filename(info.get("title", "video"))
    
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    expected_filename = os.path.join(DOWNLOADS_DIR, f"{safe_title} - {resolution}.mp4")
    
    if stream_type == "Adaptive" and best_audio:
        fmt_str = f"{video_format_id}+{best_audio.get('format_id')}"
    else:
        fmt_str = video_format_id
    
    tracker = ProgressTracker(client, chat_id, message_id, f"Downloading video at {resolution}...")
    
    # Create a shared progress state with additional fields for adaptive formats
    progress_state = {
        "downloaded": 0,
        "total": 0,
        "speed": 0,
        "eta": None,
        "last_update_time": 0,
        "update_required": asyncio.Event(),
        "finished": False,
        "stage": "video",             # Current stage: 'video', 'audio', 'merging'
        "video_size": 0,              # Total video size
        "video_downloaded": 0,        # Current video downloaded
        "audio_size": 0,              # Total audio size
        "audio_downloaded": 0,        # Current audio downloaded
        "current_filename": "",       # Current file being downloaded
        "last_update_attempt": 0,     # Time of last attempt to update progress
        "min_update_interval": 5.0,   # Increased from 2.0 seconds to 5.0 seconds
        "min_bytes_change": 3 * 1024 * 1024,  # 3MB minimum bytes change
        "last_bytes": 0,              # Track the last amount of bytes processed
        "last_percent": 0,            # Last percentage completed
        "combined_progress": True,    # Use combined progress bar for video+audio
    }
    
    # Send initial progress message
    try:
        await tracker.update_progress(0, 1, 0, None)
    except Exception as e:
        logger.error(f"Failed to send initial progress message: {e}")
        # Continue anyway - download is more important than progress updates
    
    def progress_hook(d):
        """Progress hook for yt-dlp."""
        if d['status'] == 'downloading':
            current_time = time.time()
            
            # Identify the current stage based on filename
            filename = d.get('info_dict', {}).get('_filename', '')
            if filename != progress_state["current_filename"]:
                progress_state["current_filename"] = filename
                # If we switch to a new file and already have video data, this is audio
                if progress_state["video_downloaded"] > 0 and stream_type == "Adaptive":
                    progress_state["stage"] = "audio"
                    # Don't change the main description, just add info about current stage
                    tracker.description = f"Downloading {resolution} video... (audio stream)"
            
            # Get download information
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            
            # Update stage-specific progress
            if progress_state["stage"] == "video":
                progress_state["video_downloaded"] = downloaded
                progress_state["video_size"] = total if total > 0 else progress_state["video_size"]
            elif progress_state["stage"] == "audio":
                progress_state["audio_downloaded"] = downloaded
                progress_state["audio_size"] = total if total > 0 else progress_state["audio_size"]
            
            # Calculate overall progress - combined method
            if stream_type == "Adaptive" and best_audio:
                # Combined progress: Video and audio progress as portions of the whole
                progress_state["total"] = progress_state["video_size"] + progress_state["audio_size"]
                
                if progress_state["stage"] == "video":
                    # During video stage, show just video progress
                    progress_state["downloaded"] = progress_state["video_downloaded"]
                elif progress_state["stage"] == "audio":
                    # During audio stage, show video progress + audio progress
                    progress_state["downloaded"] = progress_state["video_size"] + progress_state["audio_downloaded"]
            else:
                # For progressive format, just use the direct values
                progress_state["downloaded"] = downloaded
                progress_state["total"] = total
                
            progress_state["speed"] = d.get('speed')
            progress_state["eta"] = d.get('eta')
            
            # More conservative update strategy - update if:
            # 1. At least 5.0 seconds passed since last update
            # 2. We have significant progress (>1%) since last update
            # 3. At least 3MB downloaded since last update
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
            
            # Only set update event if conditions are met or we're at key points (start/end)
            if time_condition and (progress_condition or bytes_condition or 
                                  progress_state["downloaded"] == 0 or 
                                  progress_state["downloaded"] == progress_state["total"]):
                progress_state["last_update_time"] = current_time
                progress_state["last_bytes"] = progress_state["downloaded"]
                progress_state["update_required"].set()
        
        elif d['status'] == 'finished':
            # Only mark as fully finished if not in adaptive format or if we're in audio stage
            if stream_type != "Adaptive" or progress_state["stage"] == "audio":
                if progress_state["stage"] != "merging":
                    progress_state["stage"] = "merging"
                    tracker.description = "Processing and merging files..."
                    progress_state["update_required"].set()
            
        elif d['status'] == 'error':
            progress_state["finished"] = True
            progress_state["update_required"].set()
    
    # Task to update progress display
    async def progress_updater():
        last_percent = 0
        retry_interval = 3.0  # Start with 3 second retry (increased from 1)
        
        while not progress_state["finished"]:
            try:
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
                
                # Update progress description with stage info for better user experience
                if stream_type == "Adaptive" and progress_state["combined_progress"]:
                    # Add more detailed percentage info in the description
                    if progress_state["stage"] == "video":
                        video_percent = 0
                        if progress_state["video_size"] > 0:
                            video_percent = (progress_state["video_downloaded"] / progress_state["video_size"]) * 100
                        
                        tracker.description = f"Downloading {resolution} video... ({video_percent:.1f}% of video)"
                    
                    elif progress_state["stage"] == "audio":
                        audio_percent = 0
                        if progress_state["audio_size"] > 0:
                            audio_percent = (progress_state["audio_downloaded"] / progress_state["audio_size"]) * 100
                        
                        # Show combined info in description
                        tracker.description = f"Downloading {resolution} video... (video done, audio {audio_percent:.1f}%)"
                    
                    elif progress_state["stage"] == "merging":
                        tracker.description = f"Processing {resolution} video... (merging streams)"
                
                # Rest of the update logic
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
            except errors.FloodWaitError as e:
                # More aggressive backoff for flood wait
                logger.warning(f"Flood wait encountered during progress update: {e.seconds}s")
                retry_interval = min(e.seconds * 1.5, 30.0)  # More aggressive backoff
            except Exception as e:
                logger.error(f"Error updating progress: {e}")
                retry_interval = min(retry_interval * 2.0, 20.0)  # More aggressive exponential backoff
    
    # Start the updater task
    updater_task = asyncio.create_task(progress_updater())
    
    ydl_opts = add_cookies_to_opts({
        'format': fmt_str,
        'merge_output_format': 'mp4',
        'windowsfilenames': True,
        'outtmpl': expected_filename,
        'max_filesize': MAX_FILESIZE,
        'postprocessor_args': ['-c:a', 'aac'],
        'progress_hooks': [progress_hook],
        'verbose': False,  # Reduce console output
        'socket_timeout': 30,  # Increase socket timeout
        'retries': 10,      # Internal yt-dlp retries
        'fragment_retries': 10,  # Fragment download retries
    })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Use our custom retry function instead of direct call
            await download_with_retry(ydl, url)
        
        # Update with final progress (100%)
        if progress_state["total"] > 0:
            progress_state["finished"] = True
            tracker.description = f"Download complete for {resolution} video!"
            await tracker.update_progress(
                progress_state["total"],  # Set downloaded = total for 100%
                progress_state["total"],
                0,  # Speed is now 0
                0   # ETA is now 0
            )
        
        # Clean up the updater task
        await asyncio.sleep(0.5)  # Give it time to process final update
        if not updater_task.done():
            updater_task.cancel()
            try:
                await updater_task
            except asyncio.CancelledError:
                pass
        
        if not os.path.exists(expected_filename):
            # Try to find the actual file if outtmpl didn't work as expected
            pattern = os.path.join(DOWNLOADS_DIR, f"{safe_title}*.mp4")
            matches = glob.glob(pattern)
            if matches:
                expected_filename = matches[0]
                
    except ValueError as e:
        # Handle and log the specific error
        error_msg = str(e)
        if "ConnectionReset" in error_msg or "10054" in error_msg:
            logger.error(f"Network connection was reset during download: {error_msg}")
            # Update progress message with connection error info
            try:
                tracker.description = "Download failed due to connection reset"
                await tracker.update_progress(0, 1, 0, 0)
            except:
                pass
        # Cancel the updater task in case of error
        progress_state["finished"] = True
        if not updater_task.done():
            updater_task.cancel()
            try:
                await updater_task
            except asyncio.CancelledError:
                pass
        raise ValueError(f"Error downloading video: {str(e)}")
        
    return expected_filename, safe_title

async def download_audio_by_format(url: str, audio_format_id: str, quality_str: str, client, chat_id, message_id) -> Tuple[str, str]:
    """Download audio at specified quality with progress updates."""
    info = await extract_info(url)
    safe_title = sanitize_filename(info.get("title", "audio"))
    
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    expected_template = os.path.join(DOWNLOADS_DIR, f"{safe_title}.{quality_str}.%(ext)s")
    expected_filename = os.path.join(DOWNLOADS_DIR, f"{safe_title}.{quality_str}.mp3")
    
    tracker = ProgressTracker(client, chat_id, message_id, f"Downloading audio at {quality_str}...")
    
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
            except errors.FloodWaitError as e:
                # More aggressive backoff for flood wait
                logger.warning(f"Flood wait encountered during progress update: {e.seconds}s")
                retry_interval = min(e.seconds * 1.5, 30.0)  # More aggressive backoff
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
        'verbose': False,  # Reduce console output
        'socket_timeout': 30,  # Increase socket timeout
        'retries': 10,      # Internal yt-dlp retries
        'fragment_retries': 10,  # Fragment download retries
    })
    
    try:
        tracker.description = f"Downloading audio at {quality_str}..."
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Use our custom retry function instead of direct call
            await download_with_retry(ydl, [url])
        
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
            pattern = os.path.join(DOWNLOADS_DIR, f"{safe_title}*.mp3")
            matches = glob.glob(pattern)
            if matches:
                expected_filename = matches[0]
    except ValueError as e:
        error_msg = str(e)
        if "ConnectionReset" in error_msg or "10054" in error_msg:
            logger.error(f"Network connection was reset during audio download: {error_msg}")
            # Update progress message with connection error info
            try:
                tracker.description = "Audio download failed - connection reset"
                await tracker.update_progress(0, 1, 0, 0)
            except:
                pass
        # Cancel the updater task in case of error
        progress_state["finished"] = True
        progress_state["update_required"].set()
        if not updater_task.done():
            updater_task.cancel()
            try:
                await updater_task
            except asyncio.CancelledError:
                pass
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

async def upload_file_with_progress(client, chat_id, message_id, file_path, caption, reply_to):
    """Upload a file with progress updates."""
    file_size = os.path.getsize(file_path)
    tracker = ProgressTracker(client, chat_id, message_id, "Uploading file...")
    
    # Create a custom callback to update progress during upload
    upload_start_time = time.time()
    last_update_time = 0
    last_bytes = 0
    min_bytes_change = 3 * 1024 * 1024  # 3MB minimum change
    
    async def progress_callback(current, total):
        nonlocal last_update_time, last_bytes
        current_time = time.time()
        bytes_change = abs(current - last_bytes)
        
        # More conservative update strategy - update every 5 seconds or after 3MB
        if (current_time - last_update_time >= 5 or 
            bytes_change >= min_bytes_change or
            current == total):  # Final update
            
            last_update_time = current_time
            last_bytes = current
            elapsed = current_time - upload_start_time
            speed = current / elapsed if elapsed > 0 else 0
            remaining = (total - current) / speed if speed > 0 else None
            
            # Directly await the update since we're in an async context
            await tracker.update_progress(current, total, speed, remaining)
    
    try:
        # Upload the file with progress tracking
        await client.send_file(
            chat_id,
            file=file_path,
            caption=caption,
            reply_to=reply_to,
            supports_streaming=True if file_path.endswith('.mp4') else None,
            progress_callback=progress_callback
        )
    except Exception as e:
        await client.edit_message(
            chat_id, 
            message_id, 
            f"Error during upload: {str(e)}"
        )
        raise e

# Command handlers for Telethon

@events.register(events.NewMessage(pattern=r'/yt'))
async def yt_command(event):
    """Handle /yt command for downloading YouTube videos."""
    chat = await event.get_chat()
    await save_usage(chat, "yt")
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
    if (subs_requested):
        status_msg = await event.reply("Fetching subtitle info, please wait...")
        try:
            info = await extract_info(video_url)
            safe_title = sanitize_filename(info.get("title", "subtitle"))
            
            # Collect subtitle information
            subs_data = {}
            
            # Process regular subtitles
            if (info.get("subtitles")):
                for lang, tracks in info["subtitles"].items():
                    if "live_chat" in lang.lower():
                        continue
                    subs_data[lang] = tracks
                    
            # Process automatic captions
            if (info.get("automatic_captions")):
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
                'original_msg_id': event.message.id,  # Store original message ID
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
            'original_msg_id': event.message.id,  # Store original message ID
        }
        
        # Create buttons for video options
        buttons = []
        buttons.append([Button.inline("🎥 Video Options:", data="ignore")])
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
        
        # Update message to show initial download state
        await event.edit(f"Starting download at {resolution}... Please wait.")
        
        try:
            # Download the video with progress updates
            filename, safe_title = await download_video(
                video_url, 
                video_format_id, 
                best_audio, 
                stream_type, 
                resolution,
                event.client,
                event.chat_id,
                event.message_id
            )
            
            # Check file size before sending
            if os.path.exists(filename):  # Add existence check
                file_size = os.path.getsize(filename)
                if file_size > MAX_FILESIZE:
                    await event.edit(f"Error: File size ({file_size/(1024*1024):.1f} MB) exceeds Telegram's limit of 2 GB.")
                    safe_delete(filename)
                    return
            else:
                await event.edit("Error: Downloaded file not found.")
                return
            
            # Upload the file with progress tracking
            await upload_file_with_progress(
                event.client,
                event.chat_id,
                event.message_id,
                filename,
                f"{safe_title} [{resolution}]",
                yt_data.get('original_msg_id')
            )
            
            # Clean up the file and button
            safe_delete(filename)
            await event.delete()
            
        except Exception as e:
            await event.edit(f"Error: {str(e)}")
            # Clean up any partially downloaded files
            try:
                pattern = os.path.join(DOWNLOADS_DIR, f"*{resolution}*")
                for file_path in glob.glob(pattern):
                    safe_delete(file_path)
            except Exception as cleanup_error:
                print(f"Error during cleanup: {cleanup_error}")
            
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
        original_msg_id = main_data.get("original_msg_id")  # Get original message ID
        
        if not video_url:
            await event.edit("Session expired. Please use /yt command again.")
            return
        
        audio_format_id = selected["format"].get("format_id")
        quality_str = f"{selected['abr']}kbps"
        
        # Update message to show initial download state
        await event.edit(f"Starting download at {selected['abr']} kbps...")
        
        try:
            # Download the audio with progress updates
            filename, safe_title = await download_audio_by_format(
                video_url, 
                audio_format_id, 
                quality_str, 
                event.client, 
                event.chat_id, 
                event.message_id
            )
            
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
                
            # Upload the file with progress tracking
            await upload_file_with_progress(
                event.client,
                event.chat_id,
                event.message_id,
                filename,
                f"{safe_title} - {selected['abr']} kbps",
                original_msg_id
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
        original_msg_id = subs_data.get('original_msg_id')  # Get original message ID
        
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
            
            # Send the file as reply to original message
            await event.client.send_file(
                entity=event.chat_id,
                file=bio,
                caption=f"Subtitles ({lang}) for {safe_title}",
                reply_to=original_msg_id,  # Reply to original command message
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