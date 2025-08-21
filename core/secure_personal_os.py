#!/usr/bin/env python3
"""
Secure Personal OS - Main Orchestrator
Coordinates all security layers and services for safe automation
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Import security components
from ..security.permission_manager import PermissionManager
from ..security.credential_vault import CredentialVault
from ..security.sandbox import SandboxEnvironment

# Import browser and services
from ..browser.playwright_manager import PlaywrightManager
from ..services.gmail_service import GmailService
from ..services.calendar_service import CalendarService
from ..services.whatsapp_service import WhatsAppService

class SecurePersonalOS:
    """Main orchestrator for the Secure Personal OS"""
    
    def __init__(self, config_path: str = None):
        """Initialize Secure Personal OS with all components"""
        self.config_path = config_path
        
        # Initialize security components
        self.permission_manager = PermissionManager(config_path)
        self.credential_vault = CredentialVault()
        self.sandbox = SandboxEnvironment(self.permission_manager)
        
        # Initialize browser manager
        self.browser_manager = PlaywrightManager(self.permission_manager, self.credential_vault)
        
        # Initialize services
        self.gmail_service = GmailService(self.browser_manager, self.permission_manager)
        self.calendar_service = CalendarService(self.browser_manager, self.permission_manager)
        self.whatsapp_service = WhatsAppService(self.browser_manager, self.permission_manager)
        
        # State tracking
        self.session_active = False
        self.authenticated_services = set()
        self.session_data = {}
        
        # Set up logging
        self.logger = logging.getLogger('SecurePersonalOS')
        self._setup_logging()
        
    def _setup_logging(self):
        """Set up comprehensive logging"""
        log_dir = "/Users/sven/Desktop/MCP/personal-os/logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Main log file
        main_log = os.path.join(log_dir, "personal_os.log")
        
        # Configure logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(main_log),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    async def initialize_session(self, master_password: str) -> Tuple[bool, str]:
        """Initialize a secure Personal OS session"""
        try:
            self.logger.info("Initializing Secure Personal OS session...")
            
            # Check if system is in panic mode
            if self.permission_manager.is_panic_mode():
                return False, "System is in panic mode - all operations disabled"
            
            # Unlock credential vault
            if not self.credential_vault.unlock_vault(master_password):
                return False, "Failed to unlock credential vault"
            
            # Start browser session
            success = await self.browser_manager.start_browser_session(headless=False)
            if not success:
                return False, "Failed to start browser session"
            
            # Initialize session data
            self.session_data = {
                'session_id': f"pos_{int(datetime.now().timestamp())}",
                'started_at': datetime.now().isoformat(),
                'authenticated_services': [],
                'actions_performed': [],
                'security_events': []
            }
            
            self.session_active = True
            self.logger.info("Secure Personal OS session initialized successfully")
            
            return True, "Session initialized successfully"
            
        except Exception as e:
            self.logger.error(f"Failed to initialize session: {e}")
            return False, str(e)
    
    async def authenticate_services(self, service_credentials: Dict[str, Dict[str, Any]]) -> Dict[str, Tuple[bool, str]]:
        """Authenticate to multiple services securely"""
        results = {}
        
        try:
            # Gmail authentication
            if 'gmail' in service_credentials:
                self.logger.info("Authenticating to Gmail...")
                success, message = await self.gmail_service.authenticate(service_credentials['gmail'])
                results['gmail'] = (success, message)
                if success:
                    self.authenticated_services.add('gmail')
                    self.session_data['authenticated_services'].append('gmail')
            
            # Google Calendar authentication (usually same as Gmail)
            if 'calendar' in service_credentials or 'gmail' in self.authenticated_services:
                self.logger.info("Authenticating to Google Calendar...")
                calendar_creds = service_credentials.get('calendar', {})
                success, message = await self.calendar_service.authenticate(calendar_creds)
                results['calendar'] = (success, message)
                if success:
                    self.authenticated_services.add('calendar')
                    self.session_data['authenticated_services'].append('calendar')
            
            # WhatsApp authentication
            if 'whatsapp' in service_credentials:
                self.logger.info("Authenticating to WhatsApp Web...")
                success, message = await self.whatsapp_service.authenticate(service_credentials['whatsapp'])
                results['whatsapp'] = (success, message)
                if success:
                    self.authenticated_services.add('whatsapp')
                    self.session_data['authenticated_services'].append('whatsapp')
            
            self.logger.info(f"Authentication completed for {len(self.authenticated_services)} services")
            return results
            
        except Exception as e:
            self.logger.error(f"Error during service authentication: {e}")
            return {'error': (False, str(e))}
    
    async def get_daily_briefing(self) -> Dict[str, Any]:
        """Get a comprehensive daily briefing from all services"""
        try:
            briefing = {
                'date': datetime.now().strftime('%A, %B %d, %Y'),
                'session_id': self.session_data.get('session_id', 'unknown'),
                'authenticated_services': list(self.authenticated_services),
                'gmail': {},
                'calendar': {},
                'whatsapp': {},
                'summary': ''
            }
            
            # Gmail summary
            if 'gmail' in self.authenticated_services:
                try:
                    gmail_summary = await self.gmail_service.get_email_summary()
                    briefing['gmail'] = gmail_summary
                except Exception as e:
                    briefing['gmail'] = {'error': str(e)}
            
            # Calendar summary
            if 'calendar' in self.authenticated_services:
                try:
                    calendar_summary = await self.calendar_service.get_calendar_summary()
                    briefing['calendar'] = calendar_summary
                except Exception as e:
                    briefing['calendar'] = {'error': str(e)}
            
            # WhatsApp summary
            if 'whatsapp' in self.authenticated_services:
                try:
                    whatsapp_summary = await self.whatsapp_service.get_whatsapp_summary()
                    briefing['whatsapp'] = whatsapp_summary
                except Exception as e:
                    briefing['whatsapp'] = {'error': str(e)}
            
            # Generate summary text
            summary_parts = []
            
            if briefing['gmail'].get('unread_count', 0) > 0:
                summary_parts.append(f"📧 {briefing['gmail']['unread_count']} unread emails")
            
            if briefing['calendar'].get('todays_events_count', 0) > 0:
                summary_parts.append(f"📅 {briefing['calendar']['todays_events_count']} events today")
            
            if briefing['whatsapp'].get('unread_count', 0) > 0:
                summary_parts.append(f"💬 {briefing['whatsapp']['unread_count']} unread WhatsApp messages")
            
            briefing['summary'] = ' | '.join(summary_parts) if summary_parts else "All quiet today"
            
            self.logger.info(f"Daily briefing generated: {briefing['summary']}")
            return briefing
            
        except Exception as e:
            self.logger.error(f"Error generating daily briefing: {e}")
            return {'error': str(e)}
    
    async def execute_action(self, action: str, **kwargs) -> Tuple[bool, str, Any]:
        """Execute a secure action through the Personal OS"""
        try:
            # Log the action attempt
            action_log = {
                'action': action,
                'timestamp': datetime.now().isoformat(),
                'parameters': {k: v for k, v in kwargs.items() if 'password' not in k.lower()}
            }
            self.session_data['actions_performed'].append(action_log)
            
            # Route action to appropriate service
            if action.startswith('gmail_'):
                return await self._execute_gmail_action(action, **kwargs)
            elif action.startswith('calendar_'):
                return await self._execute_calendar_action(action, **kwargs)
            elif action.startswith('whatsapp_'):
                return await self._execute_whatsapp_action(action, **kwargs)
            elif action.startswith('system_'):
                return await self._execute_system_action(action, **kwargs)
            else:
                return False, f"Unknown action: {action}", None
                
        except Exception as e:
            self.logger.error(f"Error executing action {action}: {e}")
            return False, str(e), None
    
    async def _execute_gmail_action(self, action: str, **kwargs) -> Tuple[bool, str, Any]:
        """Execute Gmail-specific actions"""
        if 'gmail' not in self.authenticated_services:
            return False, "Gmail not authenticated", None
        
        try:
            if action == 'gmail_get_unread':
                success, count = await self.gmail_service.get_unread_count()
                return success, f"Found {count} unread emails", count
            
            elif action == 'gmail_get_recent':
                count = kwargs.get('count', 10)
                success, emails = await self.gmail_service.get_recent_emails(count)
                return success, f"Retrieved {len(emails)} emails", emails
            
            elif action == 'gmail_send':
                to = kwargs.get('to', '')
                subject = kwargs.get('subject', '')
                body = kwargs.get('body', '')
                attachments = kwargs.get('attachments', [])
                
                success, message = await self.gmail_service.send_email(to, subject, body, attachments)
                return success, message, None
            
            elif action == 'gmail_search':
                query = kwargs.get('query', '')
                max_results = kwargs.get('max_results', 20)
                success, results = await self.gmail_service.search_emails(query, max_results)
                return success, f"Found {len(results)} emails", results
            
            else:
                return False, f"Unknown Gmail action: {action}", None
                
        except Exception as e:
            return False, str(e), None
    
    async def _execute_calendar_action(self, action: str, **kwargs) -> Tuple[bool, str, Any]:
        """Execute Calendar-specific actions"""
        if 'calendar' not in self.authenticated_services:
            return False, "Calendar not authenticated", None
        
        try:
            if action == 'calendar_get_today':
                success, events = await self.calendar_service.get_todays_events()
                return success, f"Found {len(events)} events today", events
            
            elif action == 'calendar_get_upcoming':
                days = kwargs.get('days', 7)
                success, events = await self.calendar_service.get_upcoming_events(days)
                return success, f"Found {len(events)} upcoming events", events
            
            elif action == 'calendar_create':
                event_data = kwargs.get('event_data', {})
                success, message = await self.calendar_service.create_event(event_data)
                return success, message, None
            
            elif action == 'calendar_search':
                query = kwargs.get('query', '')
                max_results = kwargs.get('max_results', 20)
                success, results = await self.calendar_service.search_events(query, max_results)
                return success, f"Found {len(results)} events", results
            
            else:
                return False, f"Unknown Calendar action: {action}", None
                
        except Exception as e:
            return False, str(e), None
    
    async def _execute_whatsapp_action(self, action: str, **kwargs) -> Tuple[bool, str, Any]:
        """Execute WhatsApp-specific actions"""
        if 'whatsapp' not in self.authenticated_services:
            return False, "WhatsApp not authenticated", None
        
        try:
            if action == 'whatsapp_get_unread':
                success, count = await self.whatsapp_service.get_unread_messages_count()
                return success, f"Found {count} unread messages", count
            
            elif action == 'whatsapp_get_chats':
                count = kwargs.get('count', 10)
                success, chats = await self.whatsapp_service.get_recent_chats(count)
                return success, f"Retrieved {len(chats)} chats", chats
            
            elif action == 'whatsapp_send':
                contact = kwargs.get('contact', '')
                message = kwargs.get('message', '')
                success, result = await self.whatsapp_service.send_message(contact, message)
                return success, result, None
            
            elif action == 'whatsapp_get_messages':
                contact = kwargs.get('contact', '')
                count = kwargs.get('count', 20)
                success, messages = await self.whatsapp_service.get_chat_messages(contact, count)
                return success, f"Retrieved {len(messages)} messages", messages
            
            elif action == 'whatsapp_search':
                query = kwargs.get('query', '')
                success, results = await self.whatsapp_service.search_chats(query)
                return success, f"Found {len(results)} chats", results
            
            else:
                return False, f"Unknown WhatsApp action: {action}", None
                
        except Exception as e:
            return False, str(e), None
    
    async def _execute_system_action(self, action: str, **kwargs) -> Tuple[bool, str, Any]:
        """Execute system-level actions"""
        try:
            if action == 'system_status':
                status = {
                    'session_active': self.session_active,
                    'authenticated_services': list(self.authenticated_services),
                    'vault_locked': self.credential_vault.is_locked(),
                    'browser_status': self.browser_manager.get_session_status(),
                    'panic_mode': self.permission_manager.is_panic_mode()
                }
                return True, "System status retrieved", status
            
            elif action == 'system_screenshot':
                name = kwargs.get('name', 'manual')
                success, message, filepath = await self.browser_manager.perform_action('screenshot', name=name)
                return success, message, filepath
            
            elif action == 'system_security_log':
                event_type = kwargs.get('event_type', 'USER_ACTION')
                details = kwargs.get('details', {})
                self.permission_manager.log_security_event(event_type, details)
                return True, "Security event logged", None
            
            else:
                return False, f"Unknown system action: {action}", None
                
        except Exception as e:
            return False, str(e), None
    
    async def close_session(self) -> Tuple[bool, str]:
        """Close the Personal OS session safely"""
        try:
            self.logger.info("Closing Secure Personal OS session...")
            
            # Close browser session
            await self.browser_manager.close_session()
            
            # Lock credential vault
            self.credential_vault.lock_vault()
            
            # Save session data
            session_file = f"/Users/sven/Desktop/MCP/personal-os/logs/session_{self.session_data.get('session_id', 'unknown')}.json"
            with open(session_file, 'w') as f:
                json.dump(self.session_data, f, indent=2)
            os.chmod(session_file, 0o600)
            
            # Reset state
            self.session_active = False
            self.authenticated_services.clear()
            self.session_data = {}
            
            self.logger.info("Secure Personal OS session closed successfully")
            return True, "Session closed successfully"
            
        except Exception as e:
            self.logger.error(f"Error closing session: {e}")
            return False, str(e)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'session_active': self.session_active,
            'authenticated_services': list(self.authenticated_services),
            'vault_status': self.credential_vault.get_vault_stats(),
            'browser_status': self.browser_manager.get_session_status(),
            'sandbox_status': self.sandbox.get_sandbox_status(),
            'session_data': self.session_data,
            'security_config': {
                'panic_mode': self.permission_manager.is_panic_mode(),
                'browser_security': self.permission_manager.get_browser_security_config()
            }
        }

async def main():
    """Test the Secure Personal OS"""
    pos = SecurePersonalOS()
    
    print("🔐 Secure Personal OS - Interactive Test")
    print("=" * 50)
    
    # Get master password
    import getpass
    master_password = getpass.getpass("Enter master password for credential vault: ")
    
    # Initialize session
    success, message = await pos.initialize_session(master_password)
    print(f"Session Init: {success} - {message}")
    
    if success:
        # Get system status
        status = pos.get_system_status()
        print(f"\n📊 System Status:")
        print(f"  • Session Active: {status['session_active']}")
        print(f"  • Vault Status: {status['vault_status']['status']}")
        print(f"  • Browser Active: {status['browser_status']['active']}")
        
        # Test credentials (example - replace with real credentials)
        test_credentials = {
            'gmail': {
                'email': 'your-email@gmail.com',
                'password': 'your-app-password'
            }
        }
        
        print(f"\n🔑 Testing Authentication...")
        # Uncomment to test with real credentials:
        # auth_results = await pos.authenticate_services(test_credentials)
        # print(f"Auth Results: {auth_results}")
        
        # Test daily briefing
        print(f"\n📋 Generating Daily Briefing...")
        briefing = await pos.get_daily_briefing()
        print(f"Briefing: {briefing.get('summary', 'No summary available')}")
        
        # Close session
        print(f"\n🔒 Closing Session...")
        success, message = await pos.close_session()
        print(f"Session Close: {success} - {message}")

if __name__ == "__main__":
    asyncio.run(main())