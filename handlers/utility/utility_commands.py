import time
import math
import re
import asyncio
import aiohttp
import urllib.parse
from bs4 import BeautifulSoup
from pyrogram import Client, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from tcp_latency import measure_latency
from utils.usage import save_usage
from config import FEEDBACK_CHAT_ID

# Global storage for search results (in production, use a database)
search_results_storage = {}

# Store search results temporarily for pagination
search_cache = {}

# ---------------------------
# Start command
# ---------------------------
async def start_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "start")
    sender = message.from_user
    await message.reply(
        f"Hello {sender.first_name}, My name is Shin and I'm developed by @Mayman007tg.\n"
        "I'm a multipurpose bot that can help you with various stuff!\nUse /help to learn more about me."
    )

# ---------------------------
# Help command
# ---------------------------
async def help_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "help")
    
    # Check if user wants moderation commands only
    args = message.text.split()
    if len(args) > 1 and args[1].lower() == "mod":
        mod_help_text = (
            "\nHere's my moderation commands list:\n"
            "/ban - Ban a user\n"
            "/demote - Demote a user from admin\n"
            "/kick - Kick a user\n"
            "/mute - Mute a user\n"
            "/promote - Promote a user to admin\n"
            "/unban - Unban a user\n"
            "/unmute - Unmute a user\n"
            "/warn - Issue a warning to a user\n"
            "/warndel - Delete a warning by ID\n"
            "/warnslist - List all active warnings in chat\n"
            "/warnsuser - View warnings for a specific user\n"
        )
        await message.reply(mod_help_text)
        return
    
    help_text = (
        "\nHere's my commands list:\n"
        "/advice - Get a random advice\n"
        "/affirmation - Get a random affirmation\n"
        "/aghpb - Anime girl holding programming book\n"
        "/anime - Search Anime\n"
        "/ban - Ban a user\n"
        "/calc - Calculate mathematical expressions\n"
        "/cat - Get a random cat pic/vid/gif\n"
        "/character - Search Anime & Manga characters\n"
        "/chatid - Get the current chat ID\n"
        "/chatpfp - Get the current chat picture\n"
        "/choose - Make me choose for you\n"
        "/coinflip - Flip a coin\n"
        "/dadjoke - Get a random dad joke\n"
        "/demote - Demote a user from admin\n"
        "/dog - Get a random dog pic/vid/gif\n"
        "/echo - Repeats your words\n"
        "/feedback - Send feedback to developers\n"
        "/geekjoke - Get a random geek joke\n"
        "/gemini - Chat with Google's Gemini Pro AI\n"
        "/groupinfo - Get group's info\n"
        "/help - This message\n"
        "/imagine - Generate AI images\n"
        "/joindate - Get each member's join date in the group\n"
        "/kick - Kick a user\n"
        "/manga - Search Manga\n"
        "/meme - Get a random meme from Reddit\n"
        "/mute - Mute a user\n"
        "/pfp - Get user's profile picture\n"
        "/ping - Get bot's latency\n"
        "/promote - Promote a user to admin\n"
        "/reverse - Reverse your words\n"
        "/rps - Play Rock Paper Scissors\n"
        "/search - Search the internet\n"
        "/slot - A slot game\n"
        "/start - Bot's introduction\n"
        "/timer - Set yourself a timer\n"
        "/timerdel - Delete a timer\n"
        "/timerslist - Get a list of timers set in this chat\n"
        "/unban - Unban a user\n"
        "/unmute - Unmute a user\n"
        "/warn - Issue a warning to a user\n"
        "/warndel - Delete a warning by ID\n"
        "/warnslist - List all active warnings in chat\n"
        "/warnsuser - View warnings for a specific user\n"
        "/yt - Download videos from YouTube and other sites\n"
    )
    await message.reply(help_text)

# ---------------------------
# Ping Command Handler
# ---------------------------
async def ping_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "ping")
    
    try:
        # Measure bot response time (message processing + API call)
        start_time = time.time()
        sent_message = await message.reply("🏓 Measuring...")
        bot_response_time = int((time.time() - start_time) * 1000)
        
        # Measure network latency to Telegram servers
        try:
            telegram_latency = measure_latency(host='149.154.167.50', port=443, timeout=5)  # Telegram server IP
            if not telegram_latency or len(telegram_latency) == 0:
                network_latency_ms = "Failed"
            else:
                network_latency_ms = f"{int(telegram_latency[0])}ms"
        except:
            network_latency_ms = "Failed"
        
        # Final result
        await sent_message.edit_text(
            f"🏓 **Pong!**\n\n"
            f"**Bot Response:** `{bot_response_time}ms`\n"
            f"**Network:** `{network_latency_ms}`"
        )
        
    except Exception as e:
        await message.reply(f"❌ Error measuring latency: {str(e)}")

# ---------------------------
# Calculator command
# ---------------------------
async def calc_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "calc")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /calc <expression>\nExample: /calc 2 + 2 * 3\nSupports: +, -, *, /, %, ^ (power), ! (factorial), sin, cos, tan, log, sqrt, pi, e")
        return
    
    expression = args[1].strip()
    
    # Limit expression length to prevent abuse
    if len(expression) > 200:
        await message.reply("Error: Expression too long (max 200 characters)")
        return
    
    try:
        # Check for factorial abuse before processing
        factorial_matches = re.findall(r'(\d+)!', expression)
        for match in factorial_matches:
            if int(match) > 20:
                await message.reply("Error: Factorial input too large (max 20!)")
                return
        
        # Replace ^ with ** for exponentiation
        expression = re.sub(r'\^', '**', expression)
        
        # Replace factorial notation (e.g., 5! becomes math.factorial(5))
        expression = re.sub(r'(\d+)!', r'math.factorial(\1)', expression)
        
        # Replace common math functions with math module equivalents
        expression = re.sub(r'\bsin\b', 'math.sin', expression)
        expression = re.sub(r'\bcos\b', 'math.cos', expression)
        expression = re.sub(r'\btan\b', 'math.tan', expression)
        expression = re.sub(r'\blog\b', 'math.log', expression)
        expression = re.sub(r'\bsqrt\b', 'math.sqrt', expression)
        expression = re.sub(r'\bpi\b', 'math.pi', expression)
        expression = re.sub(r'\be\b', 'math.e', expression)
        
        # Use eval with restricted globals for safety
        allowed_names = {
            "__builtins__": {},
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
        }
        
        # Use asyncio timeout for cross-platform compatibility
        async def evaluate_expression():
            return eval(expression, allowed_names, {})
        
        try:
            result = await asyncio.wait_for(evaluate_expression(), timeout=5.0)
        except asyncio.TimeoutError:
            await message.reply("Error: Calculation timeout (too complex)")
            return
        
        # Check if result is too large
        if isinstance(result, (int, float)) and abs(result) > 1e15:
            await message.reply("Error: Result too large to display")
            return
        
        # Format the result nicely
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)
        
        await message.reply(f"**Expression:** `{args[1]}`\n**Result:** `{result}`")
        
    except ZeroDivisionError:
        await message.reply("Error: Division by zero!")
    except (SyntaxError, NameError, TypeError, ValueError) as e:
        await message.reply(f"Error: Invalid expression. {str(e)}")
    except Exception as e:
        await message.reply(f"Error: {str(e)}")

# ---------------------------
# Feedback command
# ---------------------------
async def feedback_command(client: Client, message: types.Message):
    chat = message.chat
    await save_usage(chat, "feedback")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /feedback <your message>\nExample: /feedback Great bot! Could you add more features?")
        return
    
    feedback_text = args[1].strip()
    
    # Limit feedback length
    if len(feedback_text) > 1000:
        await message.reply("Error: Feedback message too long (max 1000 characters)")
        return
    
    try:
        sender = message.from_user
        chat_info = f"Group: {chat.title}" if chat.type != "private" else "Private Chat"
        
        feedback_message = (
            f"📝 **New Feedback**\n\n"
            f"**From:** {sender.first_name}"
            f"{' ' + sender.last_name if sender.last_name else ''} "
            f"(@{sender.username if sender.username else 'No username'})\n"
            f"**User ID:** `{sender.id}`\n"
            f"**Chat:** {chat_info}\n"
            f"**Chat ID:** `{chat.id}`\n\n"
            f"**Message:**\n{feedback_text}"
        )
        
        await client.send_message(FEEDBACK_CHAT_ID, feedback_message)
        await message.reply("✅ Thank you for your feedback! Your message has been sent to the developers.")
        
    except Exception as e:
        await message.reply(f"❌ Error sending feedback: {str(e)}")

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