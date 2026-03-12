#!/bin/bash

#################################################
# Telegram Bot — Update Script for Proxmox Host
#################################################
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/rudeduns/tb-px/main/update.sh)
# Or with container ID as argument:
#   bash <(curl -fsSL https://raw.githubusercontent.com/rudeduns/tb-px/main/update.sh) 200
#################################################

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

RAW="https://raw.githubusercontent.com/rudeduns/tb-px/main"
BOT_DIR="/opt/telegram-bot"

FILES=(
    "bot.py"
    "admin.py"
    "claude_client.py"
    "config.py"
    "database.py"
    "requirements.txt"
)

# Get container ID
if [ -n "$1" ]; then
    CT_ID="$1"
else
    read -p "Container ID (e.g. 200): " CT_ID
fi

if ! pct status "$CT_ID" &>/dev/null; then
    echo -e "${RED}Container $CT_ID not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Updating bot in container $CT_ID...${NC}"

# Download each file into the container
for f in "${FILES[@]}"; do
    echo -n "  $f ... "
    pct exec "$CT_ID" -- curl -fsSL "$RAW/$f" -o "$BOT_DIR/$f"
    echo -e "${GREEN}ok${NC}"
done

# Install/update dependencies
echo -n "  pip install -r requirements.txt ... "
pct exec "$CT_ID" -- bash -c \
    "source $BOT_DIR/venv/bin/activate && pip install -r $BOT_DIR/requirements.txt -q"
echo -e "${GREEN}ok${NC}"

# Restart service
echo -n "  restarting telegram-bot ... "
pct exec "$CT_ID" -- systemctl restart telegram-bot
sleep 2
echo -e "${GREEN}ok${NC}"

# Show status
echo ""
pct exec "$CT_ID" -- systemctl status telegram-bot --no-pager -n 5
echo ""
echo -e "${GREEN}Done! Bot updated and restarted in container $CT_ID${NC}"
