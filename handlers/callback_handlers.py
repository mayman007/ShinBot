from pyrogram import Client
from handlers import handle_search_callback
from handlers import rps_callback_handler
from handlers.yt.yt_callbacks import yt_quality_button, yt_audio_button, yt_subs_callback, ignore_callback, cancel_download_callback
from handlers import handle_anime_callback
from handlers import handle_manga_callback
from handlers import handle_help_callback


# ---------- General Callback Query Handler ----------
async def button_click_handler(client: Client, callback_query):
    data = callback_query.data
    
    # Handle help callbacks
    if data.startswith("help_"):
        await handle_help_callback(client, callback_query)
        return
    
    # Handle search navigation callbacks
    if data.startswith("search_"):
        await handle_search_callback(client, callback_query)
        return
    
    # Handle RPS callbacks
    if data.startswith("rps_"):
        await rps_callback_handler(client, callback_query)
        return
    
    # Handle YouTube callbacks
    if data.startswith("yt_"):
        if data.startswith("yt_audio_"):
            await yt_audio_button(client, callback_query)
        else:
            await yt_quality_button(client, callback_query)
        return
    
    # Handle subtitle callbacks
    if data.startswith("subs_"):
        await yt_subs_callback(client, callback_query)
        return
    
    # Handle cancel download callbacks
    if data.startswith("cancel_"):
        await cancel_download_callback(client, callback_query)
        return
    
    # Handle ignore callback
    if data == "ignore":
        await ignore_callback(client, callback_query)
        return
    
    # Handle anime pagination callbacks
    if data.startswith("anime"):
        await handle_anime_callback(client, callback_query)
        return
    
    # Handle manga pagination callbacks  
    if data.startswith("manga"):
        await handle_manga_callback(client, callback_query)
        return