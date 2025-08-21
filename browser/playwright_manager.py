#!/usr/bin/env python3
"""
Playwright Browser Manager for Personal OS
Secure browser automation with permission controls and session management
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import subprocess

from security.permission_manager import PermissionManager
from security.credential_vault import CredentialVault
from personal_os import config as pos_config

class PlaywrightManager:
    def __init__(self, permission_manager: PermissionManager, credential_vault: CredentialVault):
        """Initialize Playwright manager with security components"""
        self.permission_manager = permission_manager
        self.credential_vault = credential_vault
        self.browser_process = None
        self.current_page = None
        self.session_data = {}
        pos_config.ensure_dirs()
        self.screenshot_dir = str(pos_config.screenshots_dir())
        
        # Ensure screenshot directory exists
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger('PersonalOS_Browser')
        
        # Browser security configuration
        self.browser_config = self.permission_manager.get_browser_security_config()
        
    def check_mcp_playwright_available(self) -> bool:
        """Check if Playwright MCP server is available"""
        try:
            # Test if we can connect to Playwright MCP
            result = subprocess.run(
                ['claude', 'mcp', 'test', 'playwright'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    async def start_browser_session(self, headless: bool = False) -> bool:
        """Start a secure browser session"""
        try:
            if not self.check_mcp_playwright_available():
                self.logger.error("Playwright MCP server not available")
                return False
            
            # Check if we're in panic mode
            if self.permission_manager.is_panic_mode():
                self.logger.error("Cannot start browser: System in panic mode")
                return False
            
            session_id = f"personal_os_{int(time.time())}"
            
            # Configure browser with security settings
            browser_args = {
                'headless': headless and not self.browser_config.get('capture_screenshots', True),
                'isolated_session': self.browser_config.get('isolated_session', True),
                'disable_extensions': self.browser_config.get('disable_extensions', True),
                'disable_plugins': self.browser_config.get('disable_plugins', True),
                'page_load_timeout': self.browser_config.get('page_load_timeout', 30),
                'action_timeout': self.browser_config.get('action_timeout', 10)
            }
            
            self.session_data = {
                'session_id': session_id,
                'started_at': datetime.now().isoformat(),
                'config': browser_args,
                'pages_visited': [],
                'actions_taken': []
            }
            
            self.logger.info(f"Started browser session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start browser session: {e}")
            return False
    
    async def navigate_to_url(self, url: str) -> Tuple[bool, str]:
        """Navigate to URL with permission checking"""
        try:
            # Parse domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check web access permission
            allowed, reason = self.permission_manager.check_web_access(domain)
            if not allowed:
                self.logger.warning(f"Navigation blocked: {reason}")
                return False, reason
            
            # Use Playwright MCP to navigate
            success = await self._mcp_navigate(url)
            if success:
                self.session_data['pages_visited'].append({
                    'url': url,
                    'domain': domain,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Take screenshot for audit
                if self.browser_config.get('capture_screenshots', True):
                    await self._take_screenshot(f"navigate_{domain}")
                
                self.logger.info(f"Successfully navigated to {domain}")
                return True, "Navigation successful"
            else:
                return False, "Navigation failed"
                
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False, str(e)
    
    async def perform_action(self, action_type: str, **kwargs) -> Tuple[bool, str, Any]:
        """Perform browser action with logging and validation"""
        try:
            # Log the action attempt
            action_data = {
                'type': action_type,
                'timestamp': datetime.now().isoformat(),
                'parameters': kwargs
            }
            
            self.session_data['actions_taken'].append(action_data)
            
            # Route to specific action handler
            if action_type == 'click':
                return await self._handle_click(**kwargs)
            elif action_type == 'type':
                return await self._handle_type(**kwargs)
            elif action_type == 'wait_for':
                return await self._handle_wait(**kwargs)
            elif action_type == 'screenshot':
                return await self._handle_screenshot(**kwargs)
            elif action_type == 'get_content':
                return await self._handle_get_content(**kwargs)
            else:
                return False, f"Unknown action type: {action_type}", None
                
        except Exception as e:
            self.logger.error(f"Action error: {e}")
            return False, str(e), None
    
    async def authenticate_service(self, service: str, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to a web service securely"""
        try:
            # Check action permission
            allowed, reason = self.permission_manager.check_action_permission(f"auth_{service}")
            if not allowed:
                return False, reason
            
            # Store credentials securely
            if not self.credential_vault.is_locked():
                self.credential_vault.store_credential(
                    service, 
                    credentials.get('username', 'default'),
                    credentials
                )
            
            # Service-specific authentication handlers
            if service == 'gmail':
                return await self._authenticate_gmail(credentials)
            elif service == 'google_calendar':
                return await self._authenticate_google_calendar(credentials)
            elif service == 'whatsapp':
                return await self._authenticate_whatsapp(credentials)
            else:
                return False, f"Unknown service: {service}"
                
        except Exception as e:
            self.logger.error(f"Authentication error for {service}: {e}")
            return False, str(e)
    
    async def _mcp_navigate(self, url: str) -> bool:
        """Navigate using Playwright MCP"""
        try:
            # This would use the actual Playwright MCP integration
            # For now, we'll simulate with subprocess call
            cmd = ['claude', 'mcp', 'playwright', 'navigate', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except:
            return False
    
    async def _handle_click(self, selector: str, **kwargs) -> Tuple[bool, str, Any]:
        """Handle click action"""
        try:
            # Use Playwright MCP for clicking
            cmd = ['claude', 'mcp', 'playwright', 'click', selector]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Take screenshot after click
                if self.browser_config.get('capture_screenshots', True):
                    await self._take_screenshot(f"after_click_{selector.replace(' ', '_')}")
                return True, "Click successful", result.stdout
            else:
                return False, f"Click failed: {result.stderr}", None
                
        except Exception as e:
            return False, str(e), None
    
    async def _handle_type(self, selector: str, text: str, **kwargs) -> Tuple[bool, str, Any]:
        """Handle typing action"""
        try:
            # Never log sensitive data
            log_text = text if 'password' not in selector.lower() else '[REDACTED]'
            self.logger.info(f"Typing text: {log_text}")
            
            # Use Playwright MCP for typing
            cmd = ['claude', 'mcp', 'playwright', 'type', selector, text]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0, result.stderr or "Type successful", result.stdout
            
        except Exception as e:
            return False, str(e), None
    
    async def _handle_wait(self, condition: str, timeout: int = 5000, **kwargs) -> Tuple[bool, str, Any]:
        """Handle wait conditions"""
        try:
            cmd = ['claude', 'mcp', 'playwright', 'wait', condition, str(timeout)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout//1000 + 5)
            
            return result.returncode == 0, result.stderr or "Wait successful", result.stdout
            
        except Exception as e:
            return False, str(e), None
    
    async def _take_screenshot(self, name: str) -> str:
        """Take a screenshot for audit purposes"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            cmd = ['claude', 'mcp', 'playwright', 'screenshot', filepath]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Set restrictive permissions on screenshot
                os.chmod(filepath, 0o600)
                self.logger.info(f"Screenshot saved: {filepath}")
                return filepath
            else:
                self.logger.warning(f"Screenshot failed: {result.stderr}")
                return ""
                
        except Exception as e:
            self.logger.error(f"Screenshot error: {e}")
            return ""
    
    async def _handle_screenshot(self, name: str = "manual", **kwargs) -> Tuple[bool, str, Any]:
        """Handle manual screenshot request"""
        filepath = await self._take_screenshot(name)
        if filepath:
            return True, "Screenshot saved", filepath
        else:
            return False, "Screenshot failed", None
    
    async def _handle_get_content(self, selector: str = "body", **kwargs) -> Tuple[bool, str, Any]:
        """Get page content"""
        try:
            cmd = ['claude', 'mcp', 'playwright', 'get_content', selector]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return True, "Content retrieved", result.stdout
            else:
                return False, result.stderr, None
                
        except Exception as e:
            return False, str(e), None
    
    async def _authenticate_gmail(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to Gmail"""
        try:
            # Navigate to Gmail
            success, message = await self.navigate_to_url("https://mail.google.com")
            if not success:
                return False, message
            
            # Wait for login form
            success, message, _ = await self.perform_action('wait_for', condition='[type="email"]')
            if not success:
                return False, "Gmail login form not found"
            
            # Enter email
            success, message, _ = await self.perform_action(
                'type', 
                selector='[type="email"]', 
                text=credentials.get('email', '')
            )
            if not success:
                return False, f"Failed to enter email: {message}"
            
            # Click Next
            success, message, _ = await self.perform_action('click', selector='#identifierNext')
            if not success:
                return False, f"Failed to click Next: {message}"
            
            # Wait for password field
            success, message, _ = await self.perform_action('wait_for', condition='[type="password"]')
            if not success:
                return False, "Password field not found"
            
            # Enter password
            success, message, _ = await self.perform_action(
                'type',
                selector='[type="password"]',
                text=credentials.get('password', '')
            )
            if not success:
                return False, f"Failed to enter password: {message}"
            
            # Click Sign In
            success, message, _ = await self.perform_action('click', selector='#passwordNext')
            if not success:
                return False, f"Failed to sign in: {message}"
            
            # Wait for Gmail to load
            success, message, _ = await self.perform_action(
                'wait_for', 
                condition='[role="main"]',
                timeout=15000
            )
            if success:
                self.logger.info("Successfully authenticated to Gmail")
                return True, "Gmail authentication successful"
            else:
                return False, "Gmail failed to load after authentication"
                
        except Exception as e:
            return False, f"Gmail authentication error: {e}"
    
    async def _authenticate_google_calendar(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to Google Calendar (assumes Gmail auth)"""
        try:
            success, message = await self.navigate_to_url("https://calendar.google.com")
            if not success:
                return False, message
            
            # If already authenticated via Gmail, should load directly
            success, message, _ = await self.perform_action(
                'wait_for',
                condition='[role="main"]',
                timeout=10000
            )
            
            if success:
                self.logger.info("Successfully authenticated to Google Calendar")
                return True, "Google Calendar authentication successful"
            else:
                return False, "Google Calendar authentication failed"
                
        except Exception as e:
            return False, f"Google Calendar authentication error: {e}"
    
    async def _authenticate_whatsapp(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to WhatsApp Web"""
        try:
            success, message = await self.navigate_to_url("https://web.whatsapp.com")
            if not success:
                return False, message
            
            # Wait for QR code or chat interface
            success, message, _ = await self.perform_action(
                'wait_for',
                condition='[data-ref], .qr-code',
                timeout=10000
            )
            
            if success:
                # Check if already logged in or need QR scan
                success, message, content = await self.perform_action('get_content', selector='body')
                if 'qr-code' in content.lower():
                    return True, "WhatsApp QR code ready - scan with phone to authenticate"
                else:
                    return True, "WhatsApp Web already authenticated"
            else:
                return False, "WhatsApp Web failed to load"
                
        except Exception as e:
            return False, f"WhatsApp authentication error: {e}"
    
    async def close_session(self):
        """Close browser session and cleanup"""
        try:
            if self.browser_config.get('clear_cookies_on_exit', False):
                # Clear cookies and session data
                cmd = ['claude', 'mcp', 'playwright', 'clear_cookies']
                subprocess.run(cmd, capture_output=True, timeout=5)
            
            # Close browser
            cmd = ['claude', 'mcp', 'playwright', 'close']
            subprocess.run(cmd, capture_output=True, timeout=5)
            
            # Save session data for audit
            session_file = f"{self.screenshot_dir}/session_{self.session_data.get('session_id', 'unknown')}.json"
            with open(session_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
            os.chmod(session_file, 0o600)
            
            self.logger.info("Browser session closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing session: {e}")
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status"""
        return {
            'active': self.browser_process is not None,
            'session_data': self.session_data,
            'screenshot_dir': self.screenshot_dir,
            'security_config': self.browser_config
        }

def main():
    """Test the Playwright Manager"""
    import asyncio
    from security.permission_manager import PermissionManager
    from security.credential_vault import CredentialVault
    
    async def test_browser():
        pm = PermissionManager()
        cv = CredentialVault()
        browser = PlaywrightManager(pm, cv)
        
        print("🌐 Testing Playwright Manager")
        print("=" * 40)
        
        # Test MCP availability
        available = browser.check_mcp_playwright_available()
        print(f"Playwright MCP Available: {available}")
        
        if available:
            # Start session
            success = await browser.start_browser_session()
            print(f"Browser Session Started: {success}")
            
            if success:
                # Test navigation
                success, message = await browser.navigate_to_url("https://www.google.com")
                print(f"Navigation Test: {success} - {message}")
                
                # Close session
                await browser.close_session()
                print("Session closed")
    
    asyncio.run(test_browser())

if __name__ == "__main__":
    main()
