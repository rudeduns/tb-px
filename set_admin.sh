#!/bin/bash

#################################################
# Fix Admin Rights in Telegram Bot
# Usage: ./fix_admin.sh USER_ID
#################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if USER_ID provided
if [ -z "$1" ]; then
    print_error "Usage: $0 USER_ID"
    echo "Example: $0 232846116"
    exit 1
fi

USER_ID=$1
BOT_DIR="/opt/telegram-bot"

print_info "Fixing admin rights for user ID: $USER_ID"

# Check if bot directory exists
if [ ! -d "$BOT_DIR" ]; then
    print_error "Bot directory not found: $BOT_DIR"
    exit 1
fi

# Update .env file
print_info "Updating .env file..."
if grep -q "ADMIN_USER_ID=" "$BOT_DIR/.env"; then
    sed -i "s/ADMIN_USER_ID=.*/ADMIN_USER_ID=$USER_ID/" "$BOT_DIR/.env"
    print_info ".env updated"
else
    print_error "ADMIN_USER_ID not found in .env"
    exit 1
fi

# Update database
print_info "Updating database..."
cd "$BOT_DIR"
source venv/bin/activate

python3 << EOF
import sys
sys.path.insert(0, '$BOT_DIR')
from database import Database
import sqlite3

# Update using database methods
db = Database('$BOT_DIR/bot_data.db')

# Check if user exists
conn = sqlite3.connect('$BOT_DIR/bot_data.db')
cursor = conn.cursor()

# Add or update user
cursor.execute("""
    INSERT INTO users (user_id, is_admin, is_authorized)
    VALUES ($USER_ID, 1, 1)
    ON CONFLICT(user_id) DO UPDATE SET
        is_admin = 1,
        is_authorized = 1
""")
conn.commit()

# Verify
cursor.execute("SELECT user_id, is_admin, is_authorized FROM users WHERE user_id = $USER_ID")
row = cursor.fetchone()
if row:
    print(f"User $USER_ID: admin={row[1]}, authorized={row[2]}")
else:
    print("User not found after update!")

conn.close()
EOF

print_info "Restarting bot service..."
systemctl restart telegram-bot

sleep 2

if systemctl is-active --quiet telegram-bot; then
    print_info "Bot restarted successfully!"
else
    print_warn "Bot service failed to start. Check logs:"
    echo "  journalctl -u telegram-bot -n 20"
fi

print_info "Done! Try /start in your bot now."
echo ""
echo "Your admin user ID: $USER_ID"
