#!/usr/bin/env python3
"""
WhatsApp Integration for Personal OS
Supports WhatsApp Web automation and notifications
"""

import subprocess
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

class WhatsAppIntegration:
    def __init__(self):
        self.whatsapp_web_url = "https://web.whatsapp.com"
        self.supported_browsers = [
            '/Applications/Google Chrome.app',
            '/Applications/Safari.app',
            '/Applications/Firefox.app'
        ]
    
    def get_whatsapp_status(self) -> Dict[str, Any]:
        """Check if WhatsApp Web is available"""
        available_browser = None
        
        for browser in self.supported_browsers:
            if os.path.exists(browser):
                available_browser = browser
                break
        
        if available_browser:
            browser_name = os.path.basename(available_browser).replace('.app', '')
            return {
                "status": "available",
                "browser": browser_name,
                "web_url": self.whatsapp_web_url,
                "message": f"WhatsApp Web can be accessed via {browser_name}"
            }
        else:
            return {
                "status": "unavailable",
                "error": "No supported browser found",
                "browsers_needed": ["Chrome", "Safari", "Firefox"]
            }
    
    def open_whatsapp_web(self) -> Dict[str, Any]:
        """Open WhatsApp Web in the default browser"""
        try:
            # Use macOS 'open' command to open WhatsApp Web
            result = subprocess.run(['open', self.whatsapp_web_url], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return {
                    "status": "success", 
                    "message": "WhatsApp Web opened in browser",
                    "note": "Scan QR code if not already logged in"
                }
            else:
                return {"error": f"Failed to open browser: {result.stderr}"}
                
        except Exception as e:
            return {"error": f"Browser open error: {str(e)}"}
    
    def send_message_via_browser(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp message by opening browser URL (requires manual confirmation)"""
        try:
            # WhatsApp Web direct message URL format
            # Note: This opens WhatsApp Web with pre-filled message, user still needs to press send
            encoded_message = message.replace(' ', '%20').replace('\n', '%0A')
            whatsapp_url = f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded_message}"
            
            result = subprocess.run(['open', whatsapp_url], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return {
                    "status": "opened",
                    "message": f"WhatsApp Web opened with pre-filled message to {phone_number}",
                    "note": "Please press Send button in browser to complete",
                    "action_required": True
                }
            else:
                return {"error": f"Failed to open WhatsApp Web: {result.stderr}"}
                
        except Exception as e:
            return {"error": f"WhatsApp send error: {str(e)}"}
    
    def get_whatsapp_notifications(self) -> List[Dict[str, Any]]:
        """Get WhatsApp notifications (requires system integration)"""
        # This would require deeper system integration or browser automation
        # For now, return status information
        
        try:
            # Check if WhatsApp Desktop is installed
            whatsapp_desktop = '/Applications/WhatsApp.app'
            
            if os.path.exists(whatsapp_desktop):
                return [{
                    "source": "WhatsApp Desktop",
                    "status": "installed",
                    "message": "WhatsApp Desktop app is available",
                    "note": "For notifications, enable system notifications for WhatsApp"
                }]
            else:
                return [{
                    "source": "WhatsApp Web",
                    "status": "web_only",
                    "message": "Using WhatsApp Web for messaging",
                    "note": "Install WhatsApp Desktop for better notifications"
                }]
                
        except Exception as e:
            return [{"error": f"Notification check error: {str(e)}"}]
    
    def create_whatsapp_shortcut(self, name: str, phone_number: str) -> Dict[str, Any]:
        """Create a shortcut command for quick messaging"""
        try:
            # Create a simple shell script for quick WhatsApp messaging
            shortcut_dir = os.path.expanduser("~/Desktop/MCP/personal-os/shortcuts")
            os.makedirs(shortcut_dir, exist_ok=True)
            
            shortcut_path = os.path.join(shortcut_dir, f"whatsapp_{name.lower()}.sh")
            
            shortcut_content = f'''#!/bin/bash
# WhatsApp shortcut for {name}
echo "Opening WhatsApp for {name} ({phone_number})..."

if [ -n "$1" ]; then
    # Send message with argument
    MESSAGE=$(echo "$1" | sed 's/ /%20/g')
    open "https://web.whatsapp.com/send?phone={phone_number}&text=$MESSAGE"
    echo "WhatsApp opened with message. Click Send to complete."
else
    # Just open chat
    open "https://web.whatsapp.com/send?phone={phone_number}"
    echo "WhatsApp chat opened for {name}"
fi
'''
            
            with open(shortcut_path, 'w') as f:
                f.write(shortcut_content)
            
            # Make executable
            os.chmod(shortcut_path, 0o755)
            
            return {
                "status": "created",
                "shortcut_path": shortcut_path,
                "usage": f"./whatsapp_{name.lower()}.sh 'Your message here'",
                "contact": {"name": name, "phone": phone_number}
            }
            
        except Exception as e:
            return {"error": f"Shortcut creation error: {str(e)}"}
    
    def get_whatsapp_qr_instructions(self) -> Dict[str, Any]:
        """Get instructions for setting up WhatsApp Web"""
        return {
            "setup_instructions": [
                "1. Open WhatsApp on your phone",
                "2. Tap Menu (3 dots) > Linked Devices",
                "3. Tap 'Link a Device'",
                "4. Point your phone at the QR code on WhatsApp Web",
                "5. Your web browser will be linked to WhatsApp"
            ],
            "browser_url": self.whatsapp_web_url,
            "note": "Keep your phone connected to internet for WhatsApp Web to work"
        }

def main():
    """Test the WhatsApp integration"""
    whatsapp = WhatsAppIntegration()
    
    print("💬 WhatsApp Status:")
    status = whatsapp.get_whatsapp_status()
    print(f"  • {json.dumps(status, indent=2)}")
    
    print("\n📱 WhatsApp Notifications:")
    notifications = whatsapp.get_whatsapp_notifications()
    for notif in notifications:
        print(f"  • {json.dumps(notif, indent=2)}")
    
    print("\n🔗 Setup Instructions:")
    instructions = whatsapp.get_whatsapp_qr_instructions()
    print(f"  • {json.dumps(instructions, indent=2)}")

if __name__ == "__main__":
    main()