import random
import praw
import aiohttp
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from utils.usage import save_usage

# ---------------------------
# Slot Command Handler
# ---------------------------
async def slot_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "slot")
    emojis = "🍎🍊🍐🍋🍉🍇🍓🍒"
    a, b, c = [random.choice(emojis) for _ in range(3)]
    
    try:
        sender = await event.get_sender()
        sender_name = sender.first_name if hasattr(sender, 'first_name') else "User"
        slotmachine = f"**[ {a} {b} {c} ]\n{sender_name}**,"
        
        if a == b == c:
            await event.reply(f"{slotmachine} All matching, you won! 🎉")
        elif (a == b) or (a == c) or (b == c):
            await event.reply(f"{slotmachine} 2 in a row, you won! 🎉")
        else:
            await event.reply(f"{slotmachine} No match, you lost 😢")
    except Exception as e:
        await event.reply(f"Error in slot game: {str(e)}")

# ---------------------------
# Coinflip Command Handler
# ---------------------------
async def coinflip_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "coinflip")
    
    result = random.choice(["Heads", "Tails"])
    try:
        sender = await event.get_sender()
        sender_name = sender.first_name if hasattr(sender, 'first_name') else "User"
        await event.reply(f"**{sender_name}** flipped a coin and got **{result}**!")
    except Exception as e:
        await event.reply(f"Coin flip result: **{result}**")

# ---------------------------
# Meme Command Handler (using PRAW)
# ---------------------------
async def meme_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "meme")
    
    try:
        # Initialize Reddit API
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            check_for_async=False
        )
        
        # Choose a meme subreddit
        subreddit = reddit.subreddit("Animemes")
        
        # Get hot submissions
        all_subs = []
        for submission in subreddit.hot(limit=50):
            # Filter out non-image posts and stickied posts
            if (submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif')) and 
                not submission.stickied and not submission.is_self):
                all_subs.append(submission)
        
        if not all_subs:
            await event.reply("No suitable memes found. Try again later.")
            return
            
        # Select a random submission
        random_sub = random.choice(all_subs)
        name = random_sub.title
        url = random_sub.url
        
        # Send the meme
        await event.client.send_file(chat.id, url, caption=name)
    except Exception as e:
        await event.reply(f"Error fetching meme: {str(e)}")

# ---------------------------
# Geekjoke Command Handler
# ---------------------------
async def geekjoke_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "geekjoke")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://geek-jokes.sameerkumar.website/api?format=json") as response:
                if response.status == 200:
                    data = await response.json()
                    joke = data.get('joke', '')
                    if joke:
                        await event.reply(joke)
                    else:
                        await event.reply("Couldn't fetch a joke. Try again later.")
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching joke: {str(e)}")

# ---------------------------
# Dadjoke Command Handler
# ---------------------------
async def dadjoke_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "dadjoke")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://icanhazdadjoke.com/slack") as response:
                if response.status == 200:
                    data = await response.json()
                    if 'attachments' in data and data['attachments']:
                        joke = data['attachments'][0]['text']
                        await event.reply(joke)
                    else:
                        await event.reply("Couldn't fetch a joke. Try again later.")
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching joke: {str(e)}")

# ---------------------------
# Dog Command Handler
# ---------------------------
async def dog_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "dog")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://random.dog/woof.json") as response:
                if response.status == 200:
                    data = await response.json()
                    dog_url = data.get('url', '')
                    
                    if not dog_url:
                        await event.reply("Couldn't fetch a dog image. Try again later.")
                        return
                        
                    if dog_url.endswith((".mp4", ".webm")):
                        await event.client.send_file(chat.id, dog_url, supports_streaming=True)
                    elif dog_url.endswith((".jpg", ".jpeg", ".png")):
                        await event.client.send_file(chat.id, dog_url)
                    elif dog_url.endswith(".gif"):
                        await event.client.send_file(chat.id, dog_url)
                    else:
                        await event.reply(f"Unsupported file type: {dog_url}")
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching dog image: {str(e)}")

# ---------------------------
# Affirmation Command Handler
# ---------------------------
async def affirmation_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "affirmation")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.affirmations.dev/") as response:
                if response.status == 200:
                    data = await response.json()
                    affirmation_text = data.get('affirmation', '')
                    if affirmation_text:
                        await event.reply(affirmation_text)
                    else:
                        await event.reply("Couldn't fetch an affirmation. Try again later.")
                else:
                    await event.reply(f"API Error: Status {response.status}")
    except Exception as e:
        await event.reply(f"Error fetching affirmation: {str(e)}")

# ---------------------------
# Advice Command Handler
# ---------------------------
async def advice_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "advice")
    
    try:
        headers = {"Accept": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get("https://api.adviceslip.com/advice") as response:
                data = await response.json(content_type="text/html")
                advice_text = data['slip']['advice']
                await event.reply(advice_text)
    except Exception as e:
        await event.reply(f"Error fetching advice: {str(e)}")

# ---------------------------
# Echo Command Handler
# ---------------------------
async def echo_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "echo")
    
    parts = event.message.message.split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip() == "":
        await event.reply("Type something in the message")
    else:
        text = parts[1].strip()
        # Check if input exceeds max length
        if len(text) > 4000:
            await event.reply("Message is too long! Please limit to 300 characters.")
            return
        await event.reply(text)

# ---------------------------
# Reverse Command Handler
# ---------------------------
async def reverse_command(event):
    chat = await event.get_chat()
    await save_usage(chat, "reverse")
    parts = event.message.message.split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip() == "":
        await event.reply("Type some words.")
        return
    your_words = parts[1].strip()
    # Check if input exceeds max length
    if len(your_words) > 4000:
        await event.reply("Message is too long! Please limit to 300 characters.")
        return
    t_rev = your_words[::-1].replace("@", "@\u200B").replace("&", "&\u200B")
    await event.reply(f"🔁 {t_rev}")
