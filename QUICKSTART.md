# 🚀 Quick Start Guide - Secure Personal OS

## ⚡ Fast Setup (5 minutes)

### 1. **Clone & Start** (60 seconds)
```bash
# Clone the repository
git clone https://github.com/Arnarsson/secure-personal-os.git
cd secure-personal-os

# Run the startup script (installs dependencies automatically)
./start.sh
```

### 2. **Configure Claude Desktop** (2 minutes)

The startup script will show you the configuration. Add this to your Claude Desktop config:

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "personal-os": {
      "command": "python",
      "args": ["/Users/sven/Desktop/MCP/secure-personal-os/core/personal-os-mcp-server.py"],
      "env": {
        "PYTHONPATH": "/Users/sven/Desktop/MCP/secure-personal-os"
      }
    },
    "playwright": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-playwright"]
    }
  }
}
```

### 3. **First Use** (2 minutes)

1. **Restart Claude Desktop** after config change
2. **In Claude Desktop chat**, try: "Use the secure_personal_os_daily tool to get my daily briefing"
3. **Set master password** when prompted (first time only)
4. **Authenticate services** as needed

## 🔧 Available Commands in Claude Desktop

Once configured, you can use these tools:

| Tool | Purpose | Example |
|------|---------|---------|
| `secure_personal_os_daily` | Daily briefing | "Get my daily summary" |
| `secure_personal_os_authenticate` | Login to services | "Authenticate my Gmail account" |
| `secure_personal_os_gmail` | Email operations | "Check my unread emails" |
| `secure_personal_os_calendar` | Calendar management | "What meetings do I have today?" |
| `secure_personal_os_whatsapp` | WhatsApp messaging | "Send a message via WhatsApp" |
| `secure_personal_os_system` | System status | "Check Personal OS health" |

## 🛠️ Manual Installation (Alternative)

If the startup script doesn't work:

```bash
# 1. Install Python dependencies
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Install Playwright MCP server
npm install -g @modelcontextprotocol/server-playwright

# 3. Start manually
export PYTHONPATH=$(pwd)
cd core
python personal-os-mcp-server.py
```

## 🔐 Security Setup

### First Run Security Configuration

1. **Master Password**: Choose a strong password (12+ characters)
2. **Permission Levels**: 
   - **Low**: Basic operations allowed
   - **Medium**: Email/calendar read access (default)
   - **High**: Send emails, create events
   - **Paranoid**: Require confirmation for everything

3. **Service Authentication**:
   - **Gmail**: Browser OAuth flow (secure)
   - **Calendar**: Uses Gmail session (automatic)
   - **WhatsApp**: QR code scan (one-time)

## ⚠️ Troubleshooting

### Common Issues

**❌ "MCP Server not found"**
- Check Claude Desktop config path
- Restart Claude Desktop after config changes
- Verify Python path is correct

**❌ "Playwright server failed"**
```bash
# Install/reinstall Playwright MCP
npm install -g @modelcontextprotocol/server-playwright
```

**❌ "Permission denied"**
- Run with master password
- Check security configuration
- Review audit logs in `audit-logs/`

**❌ "Browser automation failed"**
- Check if Playwright MCP server is running
- Verify browser permissions
- Try re-authenticating services

### Debug Mode

For detailed logs:
```bash
export PYTHONPATH=$(pwd)
export PERSONAL_OS_DEBUG=1
cd core
python personal-os-mcp-server.py
```

## 🎯 Example Usage

Once setup is complete, try these in Claude Desktop:

```
"Use secure_personal_os_daily to get my morning briefing"

"Use secure_personal_os_gmail to check for unread emails"

"Use secure_personal_os_calendar to see today's meetings"

"Use secure_personal_os_whatsapp to send 'Hello!' to John"
```

## 🔗 Repository

- **GitHub**: https://github.com/Arnarsson/secure-personal-os
- **Issues**: Report bugs or request features
- **Docs**: Complete documentation in `/docs/`

---

**Need help?** Check the full [README.md](README.md) or create an issue on GitHub.