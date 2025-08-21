#!/bin/bash

# Secure Personal OS Startup Script
# Modes:
#   ./start.sh web   - run FastAPI web app (default)
#   ./start.sh mcp   - run MCP server for Claude Desktop
#   ./start.sh both  - run web app in background, then MCP server

set -e  # Exit on error

echo "🔐 Starting Secure Personal OS..."
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

MODE="${1:-web}"

# Check if we're in the right directory
if [ ! -f "core/personal-os-mcp-server.py" ] || [ ! -f "webapp/app.py" ]; then
    echo "❌ Please run this script from the repo root (contains core/ and webapp/)"
    echo "Usage: cd /path/to/secure-personal-os && ./start.sh [web|mcp|both]"
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

# Set PYTHONPATH for imports
export PYTHONPATH="$(pwd):$PYTHONPATH"

if [ "$MODE" = "web" ] || [ "$MODE" = "both" ]; then
    echo "🚀 Starting Web App (FastAPI) on http://127.0.0.1:8000"
    # Allow custom host/port via env
    export PERSONAL_OS_WEB_HOST="${PERSONAL_OS_WEB_HOST:-127.0.0.1}"
    export PERSONAL_OS_WEB_PORT="${PERSONAL_OS_WEB_PORT:-8000}"
    if [ "$MODE" = "both" ]; then
        # Run in background
        uvicorn webapp.app:app --host "$PERSONAL_OS_WEB_HOST" --port "$PERSONAL_OS_WEB_PORT" &
        WEB_PID=$!
        echo "🌐 Web PID: $WEB_PID"
    else
        exec uvicorn webapp.app:app --host "$PERSONAL_OS_WEB_HOST" --port "$PERSONAL_OS_WEB_PORT"
    fi
fi

if [ "$MODE" = "mcp" ] || [ "$MODE" = "both" ]; then
    # Check for Playwright MCP server CLI presence
    if ! command -v npx &> /dev/null; then
        echo "⚠️  Node/npx not found. Install Node.js 18+ for Playwright MCP server integration."
    fi

    echo "🚀 Starting Personal OS MCP Server..."
    echo ""
    echo "📋 Claude Desktop MCP snippet (update path as needed):"
    cat <<JSON
{
  "mcpServers": {
    "personal-os": {
      "command": "python",
      "args": ["$(pwd)/core/personal-os-mcp-server.py"],
      "env": { "PYTHONPATH": "$(pwd)" }
    },
    "playwright": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-playwright"]
    }
  }
}
JSON
    echo ""
    echo "🔄 Starting MCP server (Ctrl+C to stop)..."
    cd core
    exec python personal-os-mcp-server.py
fi
