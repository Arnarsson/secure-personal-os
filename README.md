# 🔐 Secure Personal OS

A secure, browser automation-powered personal assistant that safely accesses your Gmail, Calendar, and WhatsApp with granular permission controls.

## 🌟 Features

- **🛡️ Security First**: Granular permission system, encrypted credentials, audit logging
- **📧 Gmail Integration**: Read emails, send messages, manage inbox via browser automation
- **📅 Calendar Management**: View events, create appointments, schedule management
- **💬 WhatsApp Web**: Send messages, manage chats securely
- **🤖 Claude Desktop Integration**: MCP tools for seamless AI assistant integration
- **🔍 Audit Trail**: Complete logging of all activities and security events

## 🏗️ Architecture

```
┌─ 🛡️ Security Layer ─────────────────────────┐
│  ├── Permission Manager (access control)     │
│  ├── Credential Vault (encrypted storage)    │
│  ├── Sandbox Environment (safe execution)    │
│  └── Audit Logger (activity tracking)        │
└──────────────────────────────────────────────┘
           │
┌─ 🌐 Browser Automation Layer ────────────────┐
│  ├── Playwright MCP Integration              │
│  ├── Session Management                      │
│  └── Service Authentication                  │
└──────────────────────────────────────────────┘
           │
┌─ 📱 Service Layer ───────────────────────────┐
│  ├── Gmail Service (email operations)        │
│  ├── Calendar Service (scheduling)           │
│  └── WhatsApp Service (messaging)            │
└──────────────────────────────────────────────┘
           │
┌─ 🎛️ Orchestration Layer ────────────────────┐
│  ├── SecurePersonalOS (main coordinator)     │
│  └── MCP Server (Claude Desktop integration) │
└──────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+ (for Playwright MCP)
- Claude Desktop (for MCP integration)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-username/secure-personal-os.git
cd secure-personal-os
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install Playwright MCP server**
```bash
# Install the Playwright MCP server globally
npm install -g @modelcontextprotocol/server-playwright
```

4. **Configure Claude Desktop MCP**

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "personal-os": {
      "command": "python",
      "args": ["/path/to/secure-personal-os/core/personal-os-mcp-server.py"],
      "env": {
        "PYTHONPATH": "/path/to/secure-personal-os"
      }
    },
    "playwright": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-playwright"
      ]
    }
  }
}
```

5. **Start the MCP Server**
```bash
cd core
python personal-os-mcp-server.py
```

### First Time Setup

1. **Initialize Security Configuration**
   - The system will prompt for a master password on first run
   - Configure permission levels for different operations
   - Set up credential storage encryption

2. **Authenticate Services**
   - Use `secure_personal_os_authenticate` tool in Claude Desktop
   - Authenticate Gmail (browser-based OAuth)
   - Authenticate Calendar (shared Gmail session)
   - Authenticate WhatsApp Web (QR code scan)

## 🔧 Usage

### Via Claude Desktop MCP Tools

Once configured, use these tools in Claude Desktop:

- **`secure_personal_os_daily`** - Get daily briefing (emails, calendar, tasks)
- **`secure_personal_os_authenticate`** - Authenticate with services  
- **`secure_personal_os_gmail`** - Gmail operations (read, send, search)
- **`secure_personal_os_calendar`** - Calendar management
- **`secure_personal_os_whatsapp`** - WhatsApp messaging
- **`secure_personal_os_system`** - System status and health

### Direct Python Usage

```python
from core.secure_personal_os import SecurePersonalOS

# Initialize with master password
pos = SecurePersonalOS()
await pos.initialize("your_master_password")

# Get daily briefing
briefing = await pos.get_daily_briefing()
print(briefing)

# Send an email
success, message = await pos.gmail_service.send_email(
    to="friend@example.com",
    subject="Hello from Personal OS",
    body="This email was sent securely via Personal OS!"
)
```

## 🛡️ Security Features

### Permission System
- Granular permissions for each operation type
- User approval required for sensitive actions
- Configurable security levels (low, medium, high, paranoid)

### Audit Logging
- Complete activity logs with timestamps
- Security event tracking
- Failed access attempt monitoring
- Automatic log rotation and archiving

### Credential Protection  
- AES-256 encryption for stored credentials
- Key derivation from master password
- No plaintext credential storage
- Automatic credential rotation support

### Sandbox Execution
- Restricted file system access
- Process isolation
- Resource usage monitoring
- Network access controls

## 📁 Project Structure

```
secure-personal-os/
├── core/                      # Core orchestration and MCP server
│   ├── secure_personal_os.py  # Main coordinator
│   └── personal-os-mcp-server.py # MCP server
├── security/                  # Security components
│   ├── permission_manager.py  # Access control
│   ├── credential_vault.py    # Encrypted storage
│   └── sandbox.py            # Safe execution
├── browser/                   # Browser automation
│   └── playwright_manager.py  # Playwright MCP integration
├── services/                  # Service integrations
│   ├── gmail_service.py       # Gmail automation
│   ├── calendar_service.py    # Calendar management
│   └── whatsapp_service.py    # WhatsApp messaging
├── config/                    # Configuration files
└── docs/                      # Documentation
```

## 🔍 Troubleshooting

### Common Issues

1. **MCP Server Won't Start**
   - Check Python path in Claude Desktop config
   - Verify all dependencies installed
   - Check permissions on script files

2. **Browser Automation Fails**
   - Ensure Playwright MCP server is running
   - Check browser permissions
   - Verify service authentication

3. **Permission Denied Errors**  
   - Check permission configuration
   - Verify master password
   - Review audit logs for details

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## ⚠️ Security Notice

This software provides direct access to your personal accounts. Always:
- Use strong master passwords
- Regularly review audit logs  
- Keep the software updated
- Use in trusted environments only