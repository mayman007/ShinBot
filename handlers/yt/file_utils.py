import os
import re
from .constants import DOWNLOADS_DIR

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

def get_user_downloads_dir(user_id: int) -> str:
    """Create and return a user-specific download directory."""
    user_dir = os.path.join(DOWNLOADS_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

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
