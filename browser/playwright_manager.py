#!/usr/bin/env python3
"""
Playwright Browser Manager for Personal OS
Secure browser automation with permission controls and session management
NOW USING REAL PLAYWRIGHT API - No more MCP subprocess calls!
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

# Import REAL Playwright!
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright

from security.permission_manager import PermissionManager
from security.credential_vault import CredentialVault
from personal_os import config as pos_config

class PlaywrightManager:
    def __init__(self, permission_manager: PermissionManager, credential_vault: CredentialVault):
        """Initialize Playwright manager with security components"""
        self.permission_manager = permission_manager
        self.credential_vault = credential_vault
        
        # Playwright objects
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self.session_data = {}
        pos_config.ensure_dirs()
        self.screenshot_dir = str(pos_config.screenshots_dir())
        
        # Ensure screenshot directory exists
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger('PersonalOS_Browser')
        
        # Browser security configuration
        self.browser_config = self.permission_manager.get_browser_security_config()
        
    async def start_browser_session(self, headless: bool = False) -> bool:
        """Start a secure browser session using real Playwright"""
        try:
            # Check if we're in panic mode
            if self.permission_manager.is_panic_mode():
                self.logger.error("Cannot start browser: System in panic mode")
                return False
            
            session_id = f"personal_os_{int(time.time())}"
            
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser with security settings
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',  # Required in some environments
            ]
            
            if self.browser_config.get('disable_extensions', True):
                browser_args.append('--disable-extensions')
            
            if self.browser_config.get('disable_plugins', True):
                browser_args.append('--disable-plugins')
            
            # Launch Chromium
            self.browser = await self.playwright.chromium.launch(
                headless=headless and not self.browser_config.get('capture_screenshots', True),
                args=browser_args
            )
            
            # Create browser context with viewport and user agent
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=False,
                java_script_enabled=True,
                bypass_csp=False,
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            # Set default timeouts
            self.context.set_default_timeout(
                self.browser_config.get('action_timeout', 10) * 1000
            )
            self.context.set_default_navigation_timeout(
                self.browser_config.get('page_load_timeout', 30) * 1000
            )
            
            # Create a new page
            self.page = await self.context.new_page()
            
            # Initialize session data
            self.session_data = {
                'session_id': session_id,
                'started_at': datetime.now().isoformat(),
                'config': {
                    'headless': headless,
                    'isolated_session': self.browser_config.get('isolated_session', True)
                },
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
            if not self.page:
                return False, "Browser session not started"
            
            # Parse domain from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check web access permission
            allowed, reason = self.permission_manager.check_web_access(domain)
            if not allowed:
                self.logger.warning(f"Navigation blocked: {reason}")
                return False, reason
            
            # Navigate using real Playwright
            await self.page.goto(url, wait_until='domcontentloaded')
            
            # Record navigation
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
                
        except Exception as e:
            self.logger.error(f"Navigation error: {e}")
            return False, str(e)
    
    async def perform_action(self, action_type: str, **kwargs) -> Tuple[bool, str, Any]:
        """Perform browser action with logging and validation"""
        try:
            if not self.page:
                return False, "Browser session not started", None
            
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
            elif action_type == 'key_press':
                return await self._handle_key_press(**kwargs)
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
                    credentials.get('username', credentials.get('email', 'default')),
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
    
    async def _handle_click(self, selector: str, **kwargs) -> Tuple[bool, str, Any]:
        """Handle click action using real Playwright"""
        try:
            # Wait for element and click
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if element:
                await element.click()
                
                # Take screenshot after click
                if self.browser_config.get('capture_screenshots', True):
                    await self._take_screenshot(f"after_click_{selector.replace(' ', '_')[:20]}")
                
                return True, "Click successful", None
            else:
                return False, f"Element not found: {selector}", None
                
        except Exception as e:
            return False, str(e), None
    
    async def _handle_type(self, selector: str, text: str, **kwargs) -> Tuple[bool, str, Any]:
        """Handle typing action using real Playwright"""
        try:
            # Never log sensitive data
            log_text = text if 'password' not in selector.lower() else '[REDACTED]'
            self.logger.info(f"Typing text into {selector}: {log_text}")
            
            # Wait for element and type
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if element:
                await element.fill(text)
                return True, "Type successful", None
            else:
                return False, f"Element not found: {selector}", None
            
        except Exception as e:
            return False, str(e), None
    
    async def _handle_wait(self, condition: str, timeout: int = 5000, **kwargs) -> Tuple[bool, str, Any]:
        """Handle wait conditions using real Playwright"""
        try:
            element = await self.page.wait_for_selector(condition, timeout=timeout)
            if element:
                return True, "Wait successful", None
            else:
                return False, f"Element not found: {condition}", None
            
        except Exception as e:
            return False, str(e), None
    
    async def _handle_key_press(self, key: str, **kwargs) -> Tuple[bool, str, Any]:
        """Handle key press using real Playwright"""
        try:
            await self.page.keyboard.press(key)
            return True, "Key press successful", None
        except Exception as e:
            return False, str(e), None
    
    async def _take_screenshot(self, name: str) -> str:
        """Take a screenshot for audit purposes using real Playwright"""
        try:
            if not self.page:
                return ""
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{name}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # Take screenshot using Playwright
            await self.page.screenshot(path=filepath, full_page=False)
            
            # Set restrictive permissions on screenshot
            os.chmod(filepath, 0o600)
            self.logger.info(f"Screenshot saved: {filepath}")
            return filepath
                
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
        """Get page content using real Playwright"""
        try:
            if not self.page:
                return False, "Browser session not started", None
            
            # Get all matching elements
            elements = await self.page.query_selector_all(selector)
            
            if not elements:
                # Try to get the whole page content if selector not found
                content = await self.page.content()
                return True, "Content retrieved", content
            
            # Extract text content from elements
            content_list = []
            for element in elements:
                try:
                    text = await element.inner_text()
                    content_list.append(text)
                except:
                    # If inner_text fails, try text_content
                    text = await element.text_content()
                    if text:
                        content_list.append(text)
            
            content = "\n".join(content_list)
            return True, "Content retrieved", content
                
        except Exception as e:
            return False, str(e), None
    
    async def _authenticate_gmail(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to Gmail using real Playwright"""
        try:
            # Navigate to Gmail
            success, message = await self.navigate_to_url("https://mail.google.com")
            if not success:
                return False, message
            
            # Wait for login form - Gmail might show different selectors
            try:
                # Try email input field
                email_input = await self.page.wait_for_selector(
                    'input[type="email"], input#identifierId, input[name="identifier"]',
                    timeout=10000
                )
                
                if email_input:
                    await email_input.fill(credentials.get('email', ''))
                    
                    # Click Next button
                    next_button = await self.page.wait_for_selector(
                        '#identifierNext, button:has-text("Next"), span:has-text("Next")',
                        timeout=5000
                    )
                    if next_button:
                        await next_button.click()
                    
                    # Wait for password field
                    await self.page.wait_for_timeout(2000)  # Give it time to transition
                    
                    password_input = await self.page.wait_for_selector(
                        'input[type="password"], input[name="password"], input#password',
                        timeout=10000
                    )
                    
                    if password_input:
                        await password_input.fill(credentials.get('password', ''))
                        
                        # Click Sign In button
                        signin_button = await self.page.wait_for_selector(
                            '#passwordNext, button:has-text("Next"), span:has-text("Next")',
                            timeout=5000
                        )
                        if signin_button:
                            await signin_button.click()
                        
                        # Wait for Gmail to load
                        await self.page.wait_for_timeout(5000)  # Give it time to load
                        
                        # Check if we're in Gmail
                        try:
                            await self.page.wait_for_selector(
                                '[role="main"], .AO, [gh="tl"]',  # Gmail main content areas
                                timeout=15000
                            )
                            self.logger.info("Successfully authenticated to Gmail")
                            return True, "Gmail authentication successful"
                        except:
                            # Check for 2FA or other challenges
                            if await self.page.query_selector('input[type="tel"]'):
                                return False, "2FA required - please complete manually"
                            return False, "Gmail failed to load after authentication"
                
            except Exception as e:
                self.logger.error(f"Gmail auth error: {e}")
                return False, f"Gmail authentication failed: {e}"
                
        except Exception as e:
            return False, f"Gmail authentication error: {e}"
    
    async def _authenticate_google_calendar(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to Google Calendar (assumes Gmail auth)"""
        try:
            success, message = await self.navigate_to_url("https://calendar.google.com")
            if not success:
                return False, message
            
            # If already authenticated via Gmail, should load directly
            try:
                await self.page.wait_for_selector(
                    '[role="main"], [role="grid"], .h11RHc',  # Calendar main grid
                    timeout=10000
                )
                self.logger.info("Successfully authenticated to Google Calendar")
                return True, "Google Calendar authentication successful"
            except:
                return False, "Google Calendar authentication failed"
                
        except Exception as e:
            return False, f"Google Calendar authentication error: {e}"
    
    async def _authenticate_whatsapp(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to WhatsApp Web using real Playwright"""
        try:
            success, message = await self.navigate_to_url("https://web.whatsapp.com")
            if not success:
                return False, message
            
            # Wait for QR code or chat interface
            await self.page.wait_for_timeout(3000)  # Give page time to load
            
            # Check if QR code is present
            qr_element = await self.page.query_selector('canvas[aria-label*="Scan"], .landing-wrapper canvas, [data-ref]')
            
            if qr_element:
                # Take screenshot of QR code
                await self._take_screenshot("whatsapp_qr_code")
                return True, "WhatsApp QR code ready - scan with phone to authenticate"
            else:
                # Check if already logged in
                chat_list = await self.page.query_selector('[data-testid="chat-list"], .two, [role="grid"]')
                if chat_list:
                    return True, "WhatsApp Web already authenticated"
                else:
                    return False, "WhatsApp Web status unclear - check browser"
                
        except Exception as e:
            return False, f"WhatsApp authentication error: {e}"
    
    async def close_session(self):
        """Close browser session and cleanup"""
        try:
            # Save session data for audit
            if self.session_data:
                session_file = f"{self.screenshot_dir}/session_{self.session_data.get('session_id', 'unknown')}.json"
                with open(session_file, 'w') as f:
                    json.dump(self.session_data, f, indent=2)
                os.chmod(session_file, 0o600)
            
            # Close Playwright objects
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            self.logger.info("Browser session closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing session: {e}")
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status"""
        return {
            'active': self.browser is not None and self.page is not None,
            'session_data': self.session_data,
            'screenshot_dir': self.screenshot_dir,
            'security_config': self.browser_config
        }

async def main():
    """Test the Playwright Manager with real Playwright"""
    import asyncio
    from security.permission_manager import PermissionManager
    from security.credential_vault import CredentialVault
    
    async def test_browser():
        pm = PermissionManager()
        cv = CredentialVault()
        browser = PlaywrightManager(pm, cv)
        
        print("🌐 Testing Real Playwright Manager")
        print("=" * 40)
        
        # Start session
        success = await browser.start_browser_session(headless=False)
        print(f"Browser Session Started: {success}")
        
        if success:
            # Test navigation
            success, message = await browser.navigate_to_url("https://www.google.com")
            print(f"Navigation Test: {success} - {message}")
            
            # Test screenshot
            success, message, filepath = await browser.perform_action('screenshot', name='test')
            print(f"Screenshot Test: {success} - {filepath}")
            
            # Wait a bit to see the browser
            await asyncio.sleep(3)
            
            # Close session
            await browser.close_session()
            print("Session closed")
    
    await test_browser()

if __name__ == "__main__":
    asyncio.run(main())