import os
import time
from .progress_tracker import ProgressTracker

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
            
            await tracker.update_progress(current, total, speed, remaining)
    
    try:
        # Determine file type and use appropriate sender
        if file_path.endswith('.mp4'):
            await client.send_video(
                chat_id,
                video=file_path,
                caption=caption,
                reply_to_message_id=reply_to,
                supports_streaming=True,
                progress=progress_callback
            )
        elif file_path.endswith('.mp3'):
            await client.send_audio(
                chat_id,
                audio=file_path,
                caption=caption,
                reply_to_message_id=reply_to,
                progress=progress_callback
            )
        else:
            await client.send_document(
                chat_id,
                document=file_path,
                caption=caption,
                reply_to_message_id=reply_to,
                progress=progress_callback
            )
        # Delete the status message after successful upload
        await client.delete_messages(chat_id, message_id)
    except Exception as e:
        await client.edit_message_text(
            chat_id, 
            message_id, 
            f"Error during upload: {str(e)}"
        )
        raise e
