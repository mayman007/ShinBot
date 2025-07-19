import aiohttp
import urllib.parse
from bs4 import BeautifulSoup
from pyrogram import Client, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.usage import save_usage

# Global storage for search results (in production, use a database)
search_results_storage = {}

# Store search results temporarily for pagination
search_cache = {}


# ---------------------------
# Search command
# ---------------------------
async def search_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "search")
    
    if len(message.command) < 2:
        await message.reply("❗ Please provide a search query. Example:\n`/search learn python`")
        return

    search_query = message.text.split(maxsplit=1)[1]
    
    status_msg = await message.reply("🔍 Searching...")

    search_engine = None
    all_results = []
    
    # Try DuckDuckGo first
    try:
        all_results = await search_duckduckgo(search_query)
        if all_results:
            search_engine = "DuckDuckGo"
        else:
            raise Exception("No results from DuckDuckGo")
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
        # Fallback to Bing search
        try:
            all_results = await search_bing(search_query)
            if all_results:
                search_engine = "Bing"
            else:
                raise Exception("No results from Bing")
        except Exception as e:
            print(f"Bing search failed: {e}")
            await status_msg.edit_text("❌ Search service temporarily unavailable. Please try again later.")
            return
    
    if not all_results:
        await status_msg.edit_text("❌ No results found for your query.")
        return
    
    # Store results in cache for pagination
    cache_key = f"{message.from_user.id}_{hash(search_query)}"
    search_cache[cache_key] = {
        'query': search_query,
        'results': all_results,
        'search_engine': search_engine,
        'total_pages': (len(all_results) + 4) // 5  # 5 results per page
    }
    
    # Show first page
    await show_search_page(status_msg, cache_key, 1)

async def show_search_page(message, cache_key, page):
    if cache_key not in search_cache:
        await message.edit_text("❌ Search results expired. Please search again.")
        return
    
    data = search_cache[cache_key]
    results = data['results']
    total_pages = data['total_pages']
    query = data['query']
    search_engine = data['search_engine']
    
    # Calculate start and end indices
    start_idx = (page - 1) * 5
    end_idx = min(start_idx + 5, len(results))
    page_results = results[start_idx:end_idx]
    
    # Build reply text
    reply_text = f"🔍 **Search results for:** {query}\n"
    reply_text += f"🌐 **Engine:** {search_engine}\n"
    reply_text += f"📄 Page {page} of {total_pages}\n\n"
    reply_text += "\n\n".join(page_results)
    
    # Split message if too long
    if len(reply_text) > 4096:
        reply_text = reply_text[:4090] + "..."
    
    # Create navigation buttons
    keyboard = []
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search_page:{cache_key}:{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="search_info"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_page:{cache_key}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add close button
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data=f"search_close:{cache_key}")])
    
    markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    try:
        await message.edit_text(reply_text, reply_markup=markup, disable_web_page_preview=True)
    except Exception as e:
        # If edit fails, send new message
        await message.reply(reply_text, reply_markup=markup, disable_web_page_preview=True)

# ---------------------------
# Search pagination callback handler
# ---------------------------
async def handle_search_callback(client: Client, callback_query):
    data = callback_query.data
    
    if data.startswith("search_page:"):
        _, cache_key, page = data.split(":", 2)
        page = int(page)
        await show_search_page(callback_query.message, cache_key, page)
        await callback_query.answer()
    
    elif data.startswith("search_close:"):
        _, cache_key = data.split(":", 1)
        # Clean up cache
        if cache_key in search_cache:
            del search_cache[cache_key]
        # Edit message instead of deleting
        await callback_query.message.edit_text("🔍 Search closed.")
        await callback_query.answer("Search closed")
    
    elif data == "search_info":
        await callback_query.answer("Use Previous/Next buttons to navigate", show_alert=False)

async def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, "html.parser")
    results = []
    
    # Multiple selector strategies for DuckDuckGo
    selectors = [
        ".result",
        ".web-result",
        "[class*='result']",
        ".links_main"
    ]
    
    search_results = []
    for selector in selectors:
        search_results = soup.select(selector)
        if search_results:
            break
    
    if not search_results:
        # Try finding any links with titles
        search_results = soup.find_all("a", href=True)
        search_results = [a for a in search_results if a.get_text(strip=True) and len(a.get_text(strip=True)) > 10]
    
    for result in search_results[:15]:  # Get more results for pagination
        title = None
        link = None
        snippet = "No description available"
        
        if result.name == "a":
            title = result.get_text(strip=True)
            link = result.get("href", "")
        else:
            # Try to find title and link within result
            title_elem = result.select_one("a[href]")
            if title_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.get("href", "")
            
            # Try to find snippet
            snippet_selectors = [".result__snippet", ".snippet", "[class*='snippet']"]
            for sel in snippet_selectors:
                snippet_elem = result.select_one(sel)
                if snippet_elem:
                    snippet = snippet_elem.get_text(strip=True)
                    break
        
        # Clean up link
        if link:
            if link.startswith("/l/?uddg="):
                try:
                    parsed_url = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                    if 'uddg' in parsed_url:
                        link = urllib.parse.unquote(parsed_url['uddg'][0])
                except:
                    continue
            elif link.startswith("//"):
                link = "https:" + link
            elif not link.startswith("http"):
                continue
        
        # Validate and add result
        if title and link and len(title) > 3:
            if len(snippet) > 150:
                snippet = snippet[:150] + "..."
            results.append(f"🔹 [{title}]({link})\n_{snippet}_\n")
    
    return results

async def search_bing(query):
    url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, "html.parser")
    results = []
    
    # Bing selectors
    search_results = soup.select(".b_algo")
    
    for result in search_results[:15]:  # Get more results for pagination
        title_elem = result.select_one("h2 a")
        snippet_elem = result.select_one(".b_caption p") or result.select_one(".b_snippet")
        
        if title_elem:
            title = title_elem.get_text(strip=True)
            link = title_elem.get("href", "")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else "No description available"
            
            if len(snippet) > 150:
                snippet = snippet[:150] + "..."
            
            if title and link and link.startswith("http"):
                results.append(f"🔹 [{title}]({link})\n_{snippet}_\n")
    
    return results