import time
import logging
from pyrogram.errors import FloodWait
from .file_utils import format_bytes, format_speed, format_eta

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Handles progress message updates with rate limiting and intelligent updates."""
    def __init__(self, client, chat_id, message_id, description):
        self.client = client
        self.chat_id = chat_id
        self.message_id = message_id
        self.description = description
        self.last_update_time = 0
        self.start_time = time.time()
        self.flood_wait_until = 0
        self.update_interval = 5  # Seconds between regular updates
        self.min_progress_change = 1  # Minimum percentage change to trigger update
        
    async def update_progress(self, current, total, speed=None, eta=None, force=False):
        """Update progress message if conditions are met."""
        current_time = time.time()
        
        # Skip update during flood wait period
        if current_time < self.flood_wait_until:
            return False
        
        # Calculate percentage for progress bar
        percentage = 0
        if total and total > 0:
            percentage = min(100, (current / total) * 100)
        
        # Decide whether to update based on time passed or significant progress
        time_since_update = current_time - self.last_update_time
        should_update = force or (
            time_since_update >= self.update_interval or 
            (total > 0 and time_since_update >= 2 and (percentage >= 99 or percentage <= 1)) or
            (self.last_update_time == 0)  # First update
        )
        
        if should_update:
            # Format progress message
            if total > 0:
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
                await self.client.edit_message_text(self.chat_id, self.message_id, msg)
                self.last_update_time = current_time
                return True
            except FloodWait as e:
                # Handle rate limiting
                self.flood_wait_until = current_time + e.x
                logger.info(f"Progress update rate limited for {e.x}s")
                return False
            except Exception as e:
                logger.error(f"Failed to update progress: {e}")
                return False
        
        return False
    
    def _get_progress_bar(self, percentage, length=20):
        """Generate a text-based progress bar."""
        filled_length = int(length * percentage / 100)
        bar = '█' * filled_length + '▒' * (length - filled_length)
        return f"[{bar}]"
