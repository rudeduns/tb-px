#!/bin/bash

#################################################
# Telegram Bot with Claude AI
# One-Click Proxmox Deployment Script
#################################################
# Usage: wget -qO- https://raw.githubusercontent.com/YOUR_REPO/main/proxmox-deploy.sh | bash
# Or: curl -sSL https://raw.githubusercontent.com/YOUR_REPO/main/proxmox-deploy.sh | bash
#################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║                                                        ║"
    echo "║     Telegram Bot with Claude AI                        ║"
    echo "║     Proxmox LXC Deployment                             ║"
    echo "║                                                        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}==>${NC} ${CYAN}$1${NC}\n"
}

# Check if running on Proxmox host
if ! command -v pct &> /dev/null; then
    print_error "This script must be run on a Proxmox host"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

print_banner

# Configuration
GITHUB_REPO_URL="https://github.com/rudeduns/tb-px"
REPO_RAW_URL="https://raw.githubusercontent.com/rudeduns/tb-px/main"

# Container defaults
CT_ID_DEFAULT=200
CT_HOSTNAME_DEFAULT="telegram-bot"
CT_PASSWORD_DEFAULT="telegram123"
CT_CORES_DEFAULT=2
CT_MEMORY_DEFAULT=2048
CT_SWAP_DEFAULT=512
CT_DISK_DEFAULT=8
CT_STORAGE_DEFAULT="local-lvm"

print_step "Container Configuration"

# Ask for container ID
read -p "Enter container ID [${CT_ID_DEFAULT}]: " CT_ID
CT_ID=${CT_ID:-$CT_ID_DEFAULT}

# Check if container already exists
if pct status $CT_ID &>/dev/null; then
    print_error "Container $CT_ID already exists!"
    read -p "Do you want to destroy it and create new? (yes/no): " DESTROY
    if [ "$DESTROY" = "yes" ]; then
        print_warn "Stopping and destroying container $CT_ID..."
        pct stop $CT_ID 2>/dev/null || true
        sleep 2
        pct destroy $CT_ID
        print_info "Container destroyed"
    else
        print_error "Aborted"
        exit 1
    fi
fi

# Ask for other container parameters
read -p "Enter hostname [${CT_HOSTNAME_DEFAULT}]: " CT_HOSTNAME
CT_HOSTNAME=${CT_HOSTNAME:-$CT_HOSTNAME_DEFAULT}

read -p "Enter root password [${CT_PASSWORD_DEFAULT}]: " CT_PASSWORD
CT_PASSWORD=${CT_PASSWORD:-$CT_PASSWORD_DEFAULT}

read -p "Enter CPU cores [${CT_CORES_DEFAULT}]: " CT_CORES
CT_CORES=${CT_CORES:-$CT_CORES_DEFAULT}

read -p "Enter RAM in MB [${CT_MEMORY_DEFAULT}]: " CT_MEMORY
CT_MEMORY=${CT_MEMORY:-$CT_MEMORY_DEFAULT}

read -p "Enter disk size in GB [${CT_DISK_DEFAULT}]: " CT_DISK
CT_DISK=${CT_DISK:-$CT_DISK_DEFAULT}

read -p "Enter storage [${CT_STORAGE_DEFAULT}]: " CT_STORAGE
CT_STORAGE=${CT_STORAGE:-$CT_STORAGE_DEFAULT}

print_step "Bot Configuration"

# Ask for Telegram bot token
echo -e "${YELLOW}Get your bot token from @BotFather in Telegram${NC}"
read -p "Enter Telegram Bot Token: " TELEGRAM_BOT_TOKEN
while [ -z "$TELEGRAM_BOT_TOKEN" ]; do
    print_error "Bot token cannot be empty!"
    read -p "Enter Telegram Bot Token: " TELEGRAM_BOT_TOKEN
done

# Ask for Claude API key
echo -e "${YELLOW}Get your API key from https://console.anthropic.com/${NC}"
read -p "Enter Claude API Key: " CLAUDE_API_KEY
while [ -z "$CLAUDE_API_KEY" ]; do
    print_error "API key cannot be empty!"
    read -p "Enter Claude API Key: " CLAUDE_API_KEY
done

# Ask for admin user ID
echo -e "${YELLOW}Get your Telegram user ID from @userinfobot${NC}"
read -p "Enter Admin Telegram User ID: " ADMIN_USER_ID
while [ -z "$ADMIN_USER_ID" ]; do
    print_error "Admin user ID cannot be empty!"
    read -p "Enter Admin Telegram User ID: " ADMIN_USER_ID
done

# Optional: Claude model
read -p "Enter Claude model [claude-3-5-sonnet-20241022]: " CLAUDE_MODEL
CLAUDE_MODEL=${CLAUDE_MODEL:-claude-3-5-sonnet-20241022}

print_step "Summary"
echo "Container Configuration:"
echo "  ID: $CT_ID"
echo "  Hostname: $CT_HOSTNAME"
echo "  CPU Cores: $CT_CORES"
echo "  RAM: ${CT_MEMORY}MB"
echo "  Disk: ${CT_DISK}GB"
echo "  Storage: $CT_STORAGE"
echo ""
echo "Bot Configuration:"
echo "  Telegram Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "  Claude API Key: ${CLAUDE_API_KEY:0:10}..."
echo "  Admin User ID: $ADMIN_USER_ID"
echo "  Claude Model: $CLAUDE_MODEL"
echo ""

read -p "Proceed with installation? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    print_error "Installation cancelled"
    exit 1
fi

print_step "Preparing Container"

# Check and download Debian template
TEMPLATE_NAME="debian-12-standard_12.7-1_amd64.tar.zst"
TEMPLATE_PATH="local:vztmpl/$TEMPLATE_NAME"

if ! pveam list local | grep -q "$TEMPLATE_NAME"; then
    print_info "Downloading Debian 12 template..."
    pveam download local $TEMPLATE_NAME
else
    print_info "Debian 12 template already exists"
fi

# Create container
print_info "Creating LXC container..."
pct create $CT_ID $TEMPLATE_PATH \
    --hostname $CT_HOSTNAME \
    --password "$CT_PASSWORD" \
    --cores $CT_CORES \
    --memory $CT_MEMORY \
    --swap $CT_SWAP_DEFAULT \
    --storage $CT_STORAGE \
    --rootfs $CT_STORAGE:$CT_DISK \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp,firewall=1 \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 1 \
    --start 0

print_info "Container created successfully"

# Start container
print_info "Starting container..."
pct start $CT_ID

# Wait for container to be ready
print_info "Waiting for container to start..."
sleep 10

# Wait for network
for i in {1..30}; do
    if pct exec $CT_ID -- ping -c 1 8.8.8.8 &>/dev/null; then
        print_info "Network is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Network timeout"
        exit 1
    fi
    sleep 2
done

print_step "Installing Bot"

# Update system
print_info "Updating system packages..."
pct exec $CT_ID -- bash -c "apt-get update && apt-get upgrade -y"

# Install dependencies
print_info "Installing dependencies..."
pct exec $CT_ID -- apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    nano \
    htop

# Create installation directory
INSTALL_DIR="/opt/telegram-bot"
print_info "Creating installation directory..."
pct exec $CT_ID -- mkdir -p $INSTALL_DIR

# Option 1: Download from GitHub (if available)
if curl -fsSL "$REPO_RAW_URL/bot.py" &>/dev/null; then
    print_info "Downloading bot files from GitHub..."
    for file in bot.py admin.py config.py database.py claude_client.py requirements.txt; do
        pct exec $CT_ID -- curl -fsSL "$REPO_RAW_URL/$file" -o "$INSTALL_DIR/$file"
        print_info "Downloaded: $file"
    done
else
    # Option 2: Clone entire repo
    print_warn "Direct download failed, cloning repository..."
    pct exec $CT_ID -- bash -c "cd /tmp && git clone $GITHUB_REPO_URL telegram-bot-tmp"
    pct exec $CT_ID -- bash -c "cp -r /tmp/telegram-bot-tmp/* $INSTALL_DIR/"
    pct exec $CT_ID -- rm -rf /tmp/telegram-bot-tmp
fi

# Create virtual environment
print_info "Creating Python virtual environment..."
pct exec $CT_ID -- python3 -m venv $INSTALL_DIR/venv

# Install Python packages
print_info "Installing Python packages (this may take a few minutes)..."
pct exec $CT_ID -- bash -c "cd $INSTALL_DIR && venv/bin/pip install --upgrade pip"
pct exec $CT_ID -- bash -c "cd $INSTALL_DIR && venv/bin/pip install -r requirements.txt"

# Create .env file with provided configuration
print_info "Creating configuration file..."
pct exec $CT_ID -- bash -c "cat > $INSTALL_DIR/.env << EOF
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN

# Claude API Key
CLAUDE_API_KEY=$CLAUDE_API_KEY

# Admin Telegram User ID
ADMIN_USER_ID=$ADMIN_USER_ID

# Database path
DATABASE_PATH=bot_data.db

# Claude Model
CLAUDE_MODEL=$CLAUDE_MODEL

# Maximum tokens per response
MAX_TOKENS=4096
EOF"

# Create service user
print_info "Creating service user..."
pct exec $CT_ID -- bash -c "useradd -r -m -d /home/telegram-bot -s /bin/bash telegram-bot || true"

# Set permissions
print_info "Setting permissions..."
pct exec $CT_ID -- chown -R telegram-bot:telegram-bot $INSTALL_DIR

# Create systemd service
print_info "Creating systemd service..."
pct exec $CT_ID -- bash -c "cat > /etc/systemd/system/telegram-bot.service << 'EOF'
[Unit]
Description=Telegram Bot with Claude AI
After=network.target

[Service]
Type=simple
User=telegram-bot
WorkingDirectory=$INSTALL_DIR
Environment=\"PATH=$INSTALL_DIR/venv/bin\"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/bot.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-bot

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd and enable service
print_info "Enabling service..."
pct exec $CT_ID -- systemctl daemon-reload
pct exec $CT_ID -- systemctl enable telegram-bot.service

# Start the bot
print_info "Starting bot..."
pct exec $CT_ID -- systemctl start telegram-bot.service

# Wait a bit and check status
sleep 3

print_step "Installation Complete!"

# Get container IP
CT_IP=$(pct exec $CT_ID -- hostname -I | awk '{print $1}')

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║  Bot successfully installed and started!               ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Container Details:${NC}"
echo "  Container ID: $CT_ID"
echo "  Hostname: $CT_HOSTNAME"
echo "  IP Address: $CT_IP"
echo "  Root Password: $CT_PASSWORD"
echo ""
echo -e "${CYAN}Bot Details:${NC}"
echo "  Installation Path: $INSTALL_DIR"
echo "  Service: telegram-bot.service"
echo ""
echo -e "${CYAN}Useful Commands:${NC}"
echo ""
echo "  Enter container:"
echo "    ${YELLOW}pct enter $CT_ID${NC}"
echo ""
echo "  Check bot status:"
echo "    ${YELLOW}pct exec $CT_ID -- systemctl status telegram-bot${NC}"
echo ""
echo "  View logs:"
echo "    ${YELLOW}pct exec $CT_ID -- journalctl -u telegram-bot -f${NC}"
echo ""
echo "  Restart bot:"
echo "    ${YELLOW}pct exec $CT_ID -- systemctl restart telegram-bot${NC}"
echo ""
echo "  Stop bot:"
echo "    ${YELLOW}pct exec $CT_ID -- systemctl stop telegram-bot${NC}"
echo ""
echo "  Edit configuration:"
echo "    ${YELLOW}pct exec $CT_ID -- nano $INSTALL_DIR/.env${NC}"
echo "    ${YELLOW}pct exec $CT_ID -- systemctl restart telegram-bot${NC}"
echo ""
echo -e "${GREEN}Start chatting with your bot in Telegram!${NC}"
echo ""

# Show bot status
if pct exec $CT_ID -- systemctl is-active --quiet telegram-bot; then
    print_info "Bot is running!"
    echo ""
    echo "Check logs now:"
    echo "  ${YELLOW}pct exec $CT_ID -- journalctl -u telegram-bot -n 20${NC}"
else
    print_warn "Bot service is not active. Check logs:"
    echo "  ${YELLOW}pct exec $CT_ID -- journalctl -u telegram-bot -n 50${NC}"
fi

echo ""
