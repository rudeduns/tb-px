"""Configuration management for the Telegram bot."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Claude configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")

# Claude pricing (per million tokens) - update as needed
CLAUDE_PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20240620": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}

def validate_config():
    """Validate that all required configuration is present."""
    errors = []

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is not set")

    if not CLAUDE_API_KEY:
        errors.append("CLAUDE_API_KEY is not set")

    if ADMIN_USER_ID == 0:
        errors.append("ADMIN_USER_ID is not set")

    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    return True
