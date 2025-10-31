# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot with Claude AI integration that supports:
- Text conversations with context memory
- Image analysis via Claude Vision
- Text file processing
- User authorization system with admin controls
- Token usage tracking and cost calculation

**Tech Stack**: Python 3.8+, python-telegram-bot 21.5, Anthropic API, SQLite

**Deployment**: Designed for Proxmox LXC containers, includes systemd service

## Development Commands

### Local Development

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run bot
python bot.py

# Run with debug logging
PYTHONUNBUFFERED=1 python bot.py
```

### Testing

The project currently has no automated tests. To test manually:

```bash
# Start bot locally
python bot.py

# Test in Telegram:
# 1. Send /start to check authorization
# 2. Send text message to test Claude integration
# 3. Send image to test vision
# 4. Send text file to test document processing
# 5. Test admin commands: /admin, /users, /totalstats
```

### Deployment Commands

```bash
# One-command Proxmox deployment (RECOMMENDED)
# Run on Proxmox host - creates container, installs bot, configures everything
curl -sSL https://raw.githubusercontent.com/rudeduns/tb-px/main/proxmox-deploy.sh | bash

# Or download and run manually
wget https://raw.githubusercontent.com/rudeduns/tb-px/main/proxmox-deploy.sh
chmod +x proxmox-deploy.sh
./proxmox-deploy.sh

# Install on existing Linux server
sudo ./install.sh

# Manage service (on server or in LXC container)
sudo systemctl start telegram-bot
sudo systemctl stop telegram-bot
sudo systemctl restart telegram-bot
sudo systemctl status telegram-bot

# View logs
sudo journalctl -u telegram-bot -f
sudo journalctl -u telegram-bot -n 100 --no-pager

# Manage from Proxmox host (without entering container)
pct exec 200 -- systemctl restart telegram-bot
pct exec 200 -- journalctl -u telegram-bot -f
```

## Architecture

### Core Components

**bot.py** - Main entry point
- Handles Telegram webhook/polling
- Routes messages to appropriate handlers
- Manages user authorization checks
- Implements text, photo, and document handlers
- Entry point: `main()` function

**claude_client.py** - Claude API wrapper
- `send_message()` - Standard text conversations
- `send_message_with_image()` - Image analysis (base64 encoding)
- `send_message_with_document()` - Document processing
- Returns tuple: (response_text, input_tokens, output_tokens)

**database.py** - SQLite ORM layer
- Three tables: users, usage_stats, conversations
- `is_authorized()`, `is_admin()` - Access control
- `add_message_to_history()`, `get_conversation_history()` - Context management
- `log_usage()` - Automatic cost calculation using CLAUDE_PRICING config

**admin.py** - Admin commands module
- `/admin` - Interactive panel with InlineKeyboard
- `/authorize <user_id>`, `/deauthorize <user_id>` - User management
- `/users`, `/totalstats` - Reporting
- Uses callback queries for button interactions

**config.py** - Configuration loader
- Loads from .env using python-dotenv
- `validate_config()` - Ensures required vars are set
- `CLAUDE_PRICING` dict - Per-model pricing (update when Claude changes prices)

### Data Flow

1. **User sends message** → Telegram API → `handle_message()` in bot.py
2. **Authorization check** → database.py `is_authorized()`
3. **Load conversation history** → database.py `get_conversation_history(limit=10)`
4. **Send to Claude** → claude_client.py `send_message()`
5. **Save response** → database.py `add_message_to_history()` x2 (user + assistant)
6. **Log usage** → database.py `log_usage()` → calculates cost from config.CLAUDE_PRICING
7. **Reply to user** → Telegram API

### Image Handling Flow

1. Download photo from Telegram (`photo.get_file().download_as_bytearray()`)
2. Encode to base64 (`base64.b64encode()`)
3. Create multimodal message with image source + text
4. Send to Claude Vision API
5. Process same as text message

### Database Schema

```sql
users: user_id (PK), username, first_name, last_name, is_authorized, is_admin, created_at, last_active

usage_stats: id (PK), user_id (FK), model, input_tokens, output_tokens, cost_usd, timestamp

conversations: id (PK), user_id (FK), role, content, timestamp
```

Admin user (ADMIN_USER_ID from .env) is automatically created with is_admin=1 on first run.

## Configuration

Required environment variables in `.env`:

```
TELEGRAM_BOT_TOKEN - From @BotFather
CLAUDE_API_KEY - From console.anthropic.com
ADMIN_USER_ID - Telegram user ID (get from @userinfobot)
CLAUDE_MODEL - Default: claude-3-5-sonnet-20241022
MAX_TOKENS - Default: 4096
DATABASE_PATH - Default: bot_data.db
```

## Important Implementation Details

### Conversation Context
- Limited to last 10 messages per user (`get_conversation_history(limit=10)`)
- Stored in SQLite conversations table
- `/clear` command deletes all history for user
- No automatic context pruning (consider implementing if users hit token limits)

### Token Cost Tracking
- Calculated immediately after each API response
- Uses `response.usage.input_tokens` and `response.usage.output_tokens`
- Pricing stored in config.CLAUDE_PRICING dict
- Formula: `(input_tokens / 1M * input_price) + (output_tokens / 1M * output_price)`

### Authorization System
- Users must contact admin and provide their user_id
- Admin runs `/authorize <user_id>` to grant access
- Unauthorized users get helpful message with their ID
- Admin cannot be deauthorized

### Image Processing
- Uses Claude Vision API (multimodal messages)
- Supports formats: jpeg, png, gif, webp (from Telegram's perspective, mostly jpeg)
- Images are base64-encoded for API
- Caption becomes the prompt, default: "Что изображено на этой картинке?"

### Document Processing
- Only text files accepted (mime_type starts with 'text/')
- Max size: 1MB
- UTF-8 decoding with latin-1 fallback
- Document content prepended to user's question

### Error Handling
- All handlers wrapped in try/except
- Errors logged via Python logging module
- User-friendly error messages sent to Telegram
- No retry logic (consider adding for transient API errors)

## Common Modifications

### Adding New Commands
1. Create async handler function in bot.py or admin.py
2. Add to application in main(): `application.add_handler(CommandHandler("cmd", handler))`
3. Add to /help text if user-facing

### Changing Claude Model
- Update CLAUDE_MODEL in .env
- Ensure model exists in CLAUDE_PRICING dict in config.py
- Restart bot: `systemctl restart telegram-bot`

### Adjusting Context Window
- Change limit parameter in `get_conversation_history(limit=10)` calls
- Consider token limits: Sonnet 3.5 has 200k context, but costs add up

### Adding New User Fields
1. Alter users table schema in database.py `init_database()`
2. Update `add_user()` and `get_all_users()` methods
3. Migrate existing db or recreate: `rm bot_data.db && systemctl restart telegram-bot`

## Security Considerations

- Never commit .env file (in .gitignore)
- Admin password in proxmox-setup.sh should be changed
- No rate limiting implemented (consider adding to prevent abuse)
- API keys stored in plaintext .env (acceptable for private deployments)
- SQLite allows concurrent reads but may lock on writes (fine for <100 users)

## Deployment Architecture

**Recommended**: Proxmox LXC container
- Debian 12 base
- 2 CPU cores, 2GB RAM
- systemd service for auto-start
- journald for centralized logging

**Alternative**: Any Linux server with systemd

**Not recommended**: Windows (install.sh and service won't work)

## File Organization

```
/opt/telegram-bot/          # Production installation dir
├── venv/                   # Python virtual environment
├── bot.py                  # Main bot logic
├── admin.py                # Admin commands
├── config.py               # Configuration loader
├── database.py             # SQLite ORM
├── claude_client.py        # Claude API client
├── .env                    # Secrets (not in git)
├── bot_data.db            # SQLite database
├── requirements.txt        # Python dependencies
└── install.sh             # Installation script
```

## Debugging Tips

View real-time logs:
```bash
journalctl -u telegram-bot -f
```

Check last errors:
```bash
journalctl -u telegram-bot -n 50 --no-pager | grep ERROR
```

Test configuration:
```bash
cd /opt/telegram-bot
source venv/bin/activate
python -c "import config; config.validate_config(); print('Config OK')"
```

Interactive debugging (add to code):
```python
import pdb; pdb.set_trace()
```

## Performance Notes

- SQLite is single-file, no separate DB server needed
- Conversation history grows unbounded (consider adding cleanup job)
- No caching of Claude responses (every message = API call)
- Image downloads are synchronous (could bottleneck with many concurrent users)
- No connection pooling for Telegram/Claude APIs (python-telegram-bot handles this)

## Future Enhancements to Consider

- Add automated tests (pytest + pytest-asyncio)
- Implement rate limiting per user
- Add conversation context pruning based on token count
- Support voice messages (Telegram → speech-to-text → Claude)
- Add Redis for distributed deployments
- Implement usage quotas per user
- Add /export command to download conversation history
- Support group chats (currently only private messages)
- Add metric collection (Prometheus/Grafana)
