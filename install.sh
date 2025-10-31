#!/bin/bash

#################################################
# Telegram Bot with Claude AI - Installation Script
# For Proxmox LXC Container (Debian/Ubuntu)
#################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

print_info "Starting Telegram Bot installation..."

# Installation directory
INSTALL_DIR="/opt/telegram-bot"
SERVICE_USER="telegram-bot"

# Update system
print_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
print_info "Installing dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    nano \
    htop

# Create service user
if id "$SERVICE_USER" &>/dev/null; then
    print_warn "User $SERVICE_USER already exists"
else
    print_info "Creating service user: $SERVICE_USER"
    useradd -r -m -d /home/$SERVICE_USER -s /bin/bash $SERVICE_USER
fi

# Create installation directory
print_info "Creating installation directory: $INSTALL_DIR"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# Check if this is a fresh install or update
if [ -f "bot.py" ]; then
    print_warn "Bot already installed. Backing up..."
    backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p $backup_dir
    cp -r .env bot_data.db $backup_dir/ 2>/dev/null || true
    print_info "Backup created in $INSTALL_DIR/$backup_dir"
fi

# Copy files if running from a different directory
if [ "$PWD" != "$INSTALL_DIR" ] && [ -f "bot.py" ]; then
    print_info "Copying bot files..."
    cp -r * $INSTALL_DIR/
fi

# Create Python virtual environment
print_info "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_info "Installing Python packages..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating .env configuration file..."
    cp .env.example .env

    print_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_warn "IMPORTANT: You need to configure the bot!"
    print_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Edit the .env file and add your credentials:"
    echo "  nano $INSTALL_DIR/.env"
    echo ""
    echo "Required settings:"
    echo "  1. TELEGRAM_BOT_TOKEN - Get from @BotFather"
    echo "  2. CLAUDE_API_KEY - Get from https://console.anthropic.com/"
    echo "  3. ADMIN_USER_ID - Your Telegram user ID (get from @userinfobot)"
    echo ""
fi

# Set permissions
print_info "Setting permissions..."
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

# Create systemd service
print_info "Creating systemd service..."
cat > /etc/systemd/system/telegram-bot.service <<EOF
[Unit]
Description=Telegram Bot with Claude AI
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/bot.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-bot

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
print_info "Reloading systemd..."
systemctl daemon-reload

# Enable service
print_info "Enabling service..."
systemctl enable telegram-bot.service

print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_info "Installation completed successfully!"
print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure the bot:"
echo "   nano $INSTALL_DIR/.env"
echo ""
echo "2. Start the bot:"
echo "   systemctl start telegram-bot"
echo ""
echo "3. Check status:"
echo "   systemctl status telegram-bot"
echo ""
echo "4. View logs:"
echo "   journalctl -u telegram-bot -f"
echo ""
echo "5. Stop the bot:"
echo "   systemctl stop telegram-bot"
echo ""
echo "6. Restart the bot:"
echo "   systemctl restart telegram-bot"
echo ""
print_info "Installation directory: $INSTALL_DIR"
print_info "Service user: $SERVICE_USER"
echo ""
