import yaml

with open("settings.yaml", "r") as file:
    config = yaml.safe_load(file)

    # Get settings
    BOT_TOKEN = config.get("BOT_TOKEN")
    ADMIN_ID = config.get("ADMIN_ID")
    GEMINI_API_KEY = config.get("GEMINI_API_KEY")
    HUGGINGFACE_TOKEN = config.get("HUGGINGFACE_TOKEN")
    REDDIT_CLIENT_ID = config.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = config.get("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = config.get("REDDIT_USER_AGENT")

    DEBUG = config.get("DEBUG")
    ENABLE_GEMINI_COMMAND = config.get("ENABLE_GEMINI_COMMAND")
    ENABLE_IMAGINE_COMMAND = config.get("ENABLE_IMAGINE_COMMAND")
    ENABLE_MEME_COMMAND = config.get("ENABLE_MEME_COMMAND")