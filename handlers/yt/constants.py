import os

# Constants
MAX_FILESIZE = 2147483648  # 2GB max file size for Telegram
COOKIES_FILE = 'cookies.txt'
DOWNLOADS_DIR = 'downloads'  # Base downloads directory
MAX_RETRIES = 3  # Maximum number of retry attempts
INITIAL_RETRY_DELAY = 2  # Initial delay between retries in seconds
MAX_RETRY_DELAY = 10  # Maximum delay between retries in seconds

# Track active downloads per user (make it a proper singleton with global scope)
active_downloads = {}
download_locks = {}  # Add locks per user to prevent race conditions
# Track cancellation requests
download_cancellations = {}  # user_id -> True if cancelled

# Ensure downloads directory exists
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
