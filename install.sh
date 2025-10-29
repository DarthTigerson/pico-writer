#!/bin/bash

# PicoWriter Installation Script
# This script installs PicoWriter to the system

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/picowriter"
LAUNCHER_DIR="/root/command-launcher"
LAUNCHER_SCRIPT="$LAUNCHER_DIR/picowriter.sh"
BIN_LINK="/usr/local/bin/picowriter"

echo -e "${GREEN}PicoWriter Installation Script${NC}"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Get the directory where the script is located (or current directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$SCRIPT_DIR"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}Error: Source directory not found: $SOURCE_DIR${NC}"
    exit 1
fi

# Check if main.py exists
if [ ! -f "$SOURCE_DIR/main.py" ]; then
    echo -e "${RED}Error: main.py not found in source directory${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Copying PicoWriter to $INSTALL_DIR${NC}"
# Remove old installation if it exists
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing existing installation..."
    rm -rf "$INSTALL_DIR"
fi

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Copy all files (excluding .git and other unnecessary files)
echo "Copying files..."
rsync -a --exclude='.git' --exclude='*.pyc' --exclude='__pycache__' \
    --exclude='.gitignore' \
    "$SOURCE_DIR/" "$INSTALL_DIR/"

# Make main.py executable
chmod +x "$INSTALL_DIR/main.py"

echo -e "${GREEN}✓ Files copied successfully${NC}"
echo ""

# Step 2: Create launcher script in /root/command-launcher
echo -e "${YELLOW}Step 2: Creating launcher script${NC}"
mkdir -p "$LAUNCHER_DIR"

# Create launcher script
cat > "$LAUNCHER_SCRIPT" << 'EOF'
#!/bin/bash
# PicoWriter Launcher Script
cd /opt/picowriter
python3 main.py "$@"
EOF

chmod +x "$LAUNCHER_SCRIPT"
echo -e "${GREEN}✓ Launcher script created at $LAUNCHER_SCRIPT${NC}"
echo ""

# Step 3: Create system-wide command link
echo -e "${YELLOW}Step 3: Creating system-wide command${NC}"
# Remove existing link if it exists
if [ -L "$BIN_LINK" ] || [ -f "$BIN_LINK" ]; then
    rm -f "$BIN_LINK"
fi

# Create symlink for system-wide access
ln -s "$LAUNCHER_SCRIPT" "$BIN_LINK"
echo -e "${GREEN}✓ System-wide command created: picowriter${NC}"
echo ""

# Verify installation
echo -e "${YELLOW}Verifying installation...${NC}"
if [ -f "$INSTALL_DIR/main.py" ] && [ -f "$LAUNCHER_SCRIPT" ] && [ -L "$BIN_LINK" ]; then
    echo -e "${GREEN}✓ Installation verified successfully${NC}"
else
    echo -e "${RED}✗ Installation verification failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}================================"
echo "Installation Complete!"
echo "================================"
echo -e "${NC}"
echo "PicoWriter has been installed to: $INSTALL_DIR"
echo "Launcher script: $LAUNCHER_SCRIPT"
echo "System command: picowriter"
echo ""
echo "You can now launch PicoWriter by typing: ${GREEN}picowriter${NC}"
echo ""
