#!/bin/bash

# Secure Personal OS Startup Script
# This script helps you start the Personal OS MCP server

set -e  # Exit on error

echo "🔐 Starting Secure Personal OS..."
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "core/personal-os-mcp-server.py" ]; then
    echo "❌ Please run this script from the personal-os directory"
    echo "Usage: cd /path/to/personal-os && ./start.sh"
    exit 1
fi

# Install dependencies if requirements.txt has changed
if [ requirements.txt -nt .venv/pyvenv.cfg ] 2>/dev/null; then
    echo "📦 Installing/updating dependencies..."
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -r requirements.txt
else
    echo "📦 Activating virtual environment..."
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "⚠️  No virtual environment found. Installing dependencies..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
    fi
fi

# Check for Playwright MCP server
if ! command -v npx &> /dev/null || ! npx @modelcontextprotocol/server-playwright --help &> /dev/null; then
    echo "⚠️  Playwright MCP server not found."
    echo "Installing Playwright MCP server..."
    npm install -g @modelcontextprotocol/server-playwright
fi

# Set PYTHONPATH
export PYTHONPATH="$(pwd):$PYTHONPATH"

echo "🚀 Starting Personal OS MCP Server..."
echo ""
echo "📋 Configuration needed in Claude Desktop:"
echo "Add this to your claude_desktop_config.json:"
echo ""
echo "{"
echo "  \"mcpServers\": {"
echo "    \"personal-os\": {"
echo "      \"command\": \"python\","
echo "      \"args\": [\"$(pwd)/core/personal-os-mcp-server.py\"],"
echo "      \"env\": {"
echo "        \"PYTHONPATH\": \"$(pwd)\""
echo "      }"
echo "    },"
echo "    \"playwright\": {"
echo "      \"command\": \"npx\","
echo "      \"args\": [\"@modelcontextprotocol/server-playwright\"]"
echo "    }"
echo "  }"
echo "}"
echo ""
echo "🔄 Starting server (press Ctrl+C to stop)..."
echo ""

# Start the MCP server
cd core
python personal-os-mcp-server.py