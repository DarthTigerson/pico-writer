#!/bin/bash

# PicoWriter Uninstallation Script
# This script removes PicoWriter from the system

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/picowriter"
LAUNCHER_SCRIPT="/root/command-launcher/picowriter.sh"
BIN_LINK="/usr/local/bin/picowriter"

echo -e "${YELLOW}PicoWriter Uninstallation Script${NC}"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Confirm uninstallation
read -p "Are you sure you want to uninstall PicoWriter? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo -e "${YELLOW}Removing PicoWriter...${NC}"

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing installation directory..."
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓ Installation directory removed${NC}"
else
    echo -e "${YELLOW}Installation directory not found${NC}"
fi

# Remove launcher script
if [ -f "$LAUNCHER_SCRIPT" ]; then
    echo "Removing launcher script..."
    rm -f "$LAUNCHER_SCRIPT"
    echo -e "${GREEN}✓ Launcher script removed${NC}"
else
    echo -e "${YELLOW}Launcher script not found${NC}"
fi

# Remove system command link
if [ -L "$BIN_LINK" ] || [ -f "$BIN_LINK" ]; then
    echo "Removing system command..."
    rm -f "$BIN_LINK"
    echo -e "${GREEN}✓ System command removed${NC}"
else
    echo -e "${YELLOW}System command not found${NC}"
fi

echo ""
echo -e "${GREEN}PicoWriter has been uninstalled successfully${NC}"
echo ""
