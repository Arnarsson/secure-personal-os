#!/usr/bin/env python3
"""
WhatsApp Web Service Integration for Personal OS
Secure WhatsApp Web access using browser automation for messaging
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

from browser.playwright_manager import PlaywrightManager
from security.permission_manager import PermissionManager

class WhatsAppService:
    def __init__(self, playwright_manager: PlaywrightManager, permission_manager: PermissionManager):
        """Initialize WhatsApp service with browser automation"""
        self.browser = playwright_manager
        self.permission_manager = permission_manager
        self.authenticated = False
        self.current_chat = None
        
        # Set up logging
        self.logger = logging.getLogger('PersonalOS_WhatsApp')
        
    async def authenticate(self, credentials: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Authenticate to WhatsApp Web (QR code based)"""
        try:
            # Check permission for WhatsApp access
            allowed, reason = self.permission_manager.check_action_permission("whatsapp_auth")
            if not allowed:
                return False, reason
            
            success, message = await self.browser.authenticate_service('whatsapp', credentials or {})
            if success:
                # Check if we need QR code or if already authenticated
                if "QR code ready" in message:
                    self.logger.info("WhatsApp Web QR code displayed - scan with phone")
                    return True, "QR code displayed - scan with your phone to authenticate"
                else:
                    self.authenticated = True
                    self.logger.info("WhatsApp Web already authenticated")
                    return True, "WhatsApp Web authentication successful"
            else:
                return False, message
                
        except Exception as e:
            self.logger.error(f"WhatsApp authentication error: {e}")
            return False, str(e)
    
    async def check_authentication_status(self) -> Tuple[bool, str]:
        """Check if WhatsApp Web is fully authenticated"""
        try:
            # Look for main chat interface
            success, message, content = await self.browser.perform_action(
                'get_content',
                selector='[data-testid="chat-list"], .two, ._2Ts6i'
            )
            
            if success and content and 'data-testid="chat-list"' in content:
                self.authenticated = True
                return True, "Fully authenticated and chat list loaded"
            else:
                # Check if QR code is still displayed
                success, message, qr_content = await self.browser.perform_action(
                    'get_content',
                    selector='[data-ref="qr-code"], .qr-code, ._2EZ_m'
                )
                
                if success and qr_content and ('qr' in qr_content.lower() or 'scan' in qr_content.lower()):
                    return False, "QR code still displayed - waiting for phone scan"
                else:
                    return False, "Authentication status unclear"
                    
        except Exception as e:
            self.logger.error(f"Error checking authentication status: {e}")
            return False, str(e)
    
    async def get_unread_messages_count(self) -> Tuple[bool, int]:
        """Get number of unread messages"""
        try:
            if not self.authenticated:
                return False, 0
            
            # Look for unread message indicators
            success, message, content = await self.browser.perform_action(
                'get_content',
                selector='[data-testid="unread-count"], ._1pJ9J, .OUeyt'
            )
            
            if success and content:
                # Extract numbers from unread indicators
                numbers = re.findall(r'\d+', content)
                if numbers:
                    total_unread = sum(int(num) for num in numbers)
                    self.logger.info(f"Found {total_unread} unread messages")
                    return True, total_unread
            
            return True, 0
            
        except Exception as e:
            self.logger.error(f"Error getting unread messages count: {e}")
            return False, 0
    
    async def get_recent_chats(self, count: int = 10) -> Tuple[bool, List[Dict[str, Any]]]:
        """Get recent chats from chat list"""
        try:
            if not self.authenticated:
                return False, []
            
            # Get chat list elements
            success, message, content = await self.browser.perform_action(
                'get_content',
                selector='[data-testid="chat-list"] > div, ._2nY6U > div'
            )
            
            chats = []
            if success and content:
                # Parse chat elements (simplified parsing)
                chat_elements = content.split('</div>')[:count]
                
                for i, chat_html in enumerate(chat_elements):
                    if not chat_html.strip():
                        continue
                    
                    try:
                        chat_data = {
                            'id': f"chat_{i}",
                            'name': self._extract_chat_name(chat_html),
                            'last_message': self._extract_last_message(chat_html),
                            'time': self._extract_message_time(chat_html),
                            'unread_count': self._extract_unread_count(chat_html),
                            'is_group': self._is_group_chat(chat_html),
                            'online_status': self._extract_online_status(chat_html)
                        }
                        chats.append(chat_data)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse chat {i}: {e}")
                        continue
            
            self.logger.info(f"Retrieved {len(chats)} recent chats")
            return True, chats
            
        except Exception as e:
            self.logger.error(f"Error getting recent chats: {e}")
            return False, []
    
    async def send_message(self, contact: str, message: str) -> Tuple[bool, str]:
        """Send a message to a contact or group"""
        try:
            if not self.authenticated:
                return False, "Not authenticated"
            
            # Check permission for sending messages
            allowed, reason = self.permission_manager.check_action_permission("send_message")
            if not allowed:
                return False, reason
            
            # Search for the contact
            success, search_message = await self._search_and_select_chat(contact)
            if not success:
                return False, f"Failed to find contact '{contact}': {search_message}"
            
            # Wait for message input box
            success, message_box_msg, _ = await self.browser.perform_action(
                'wait_for',
                condition='[data-testid="conversation-compose-box-input"], ._13NKt',
                timeout=5000
            )
            if not success:
                return False, "Message input box not found"
            
            # Type the message
            success, type_msg, _ = await self.browser.perform_action(
                'type',
                selector='[data-testid="conversation-compose-box-input"], ._13NKt',
                text=message
            )
            if not success:
                return False, f"Failed to type message: {type_msg}"
            
            # Take screenshot before sending for audit
            await self.browser.perform_action('screenshot', name='before_send_whatsapp_message')
            
            # Send the message (Enter key)
            success, send_msg, _ = await self.browser.perform_action(
                'key_press',
                key='Enter'
            )
            
            if success:
                self.logger.info(f"WhatsApp message sent to {contact}: {message[:50]}...")
                
                # Log the action for audit
                self.permission_manager.log_security_event("WHATSAPP_MESSAGE_SENT", {
                    "contact": contact,
                    "message_length": len(message),
                    "message_preview": message[:50] + "..." if len(message) > 50 else message
                })
                
                return True, "Message sent successfully"
            else:
                return False, f"Failed to send message: {send_msg}"
                
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False, str(e)
    
    async def get_chat_messages(self, contact: str, count: int = 20) -> Tuple[bool, List[Dict[str, Any]]]:
        """Get recent messages from a specific chat"""
        try:
            if not self.authenticated:
                return False, []
            
            # Select the chat
            success, message = await self._search_and_select_chat(contact)
            if not success:
                return False, []
            
            # Get message elements
            success, message_msg, content = await self.browser.perform_action(
                'get_content',
                selector='[data-testid="msg-container"], .message-in, .message-out'
            )
            
            messages = []
            if success and content:
                # Parse message elements (simplified)
                message_elements = content.split('</div>')[-count:]  # Get last N messages
                
                for i, msg_html in enumerate(message_elements):
                    if not msg_html.strip():
                        continue
                    
                    try:
                        message_data = {
                            'id': f"msg_{i}",
                            'text': self._extract_message_text(msg_html),
                            'sender': self._extract_message_sender(msg_html),
                            'time': self._extract_message_time(msg_html),
                            'is_outgoing': self._is_outgoing_message(msg_html),
                            'is_media': self._is_media_message(msg_html),
                            'message_type': self._get_message_type(msg_html)
                        }
                        messages.append(message_data)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse message {i}: {e}")
                        continue
            
            self.logger.info(f"Retrieved {len(messages)} messages from {contact}")
            return True, messages
            
        except Exception as e:
            self.logger.error(f"Error getting chat messages: {e}")
            return False, []
    
    async def search_chats(self, query: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Search for chats by name or content"""
        try:
            if not self.authenticated:
                return False, []
            
            # Click search button
            success, search_msg, _ = await self.browser.perform_action(
                'click',
                selector='[data-testid="search"], ._1WTqU, [title="Search"]'
            )
            if not success:
                return False, []
            
            # Enter search query
            success, type_msg, _ = await self.browser.perform_action(
                'type',
                selector='[data-testid="chat-list-search"], ._13NKt[type="text"]',
                text=query
            )
            if not success:
                return False, []
            
            # Wait for search results
            success, wait_msg, _ = await self.browser.perform_action(
                'wait_for',
                condition='[data-testid="search-result"], ._2nY6U div',
                timeout=5000
            )
            
            if success:
                # Get search results
                success, results_msg, content = await self.browser.perform_action(
                    'get_content',
                    selector='[data-testid="search-result"], ._2nY6U div'
                )
                
                if success and content:
                    # Parse search results
                    results = self._parse_search_results(content)
                    return True, results
            
            return True, []
            
        except Exception as e:
            self.logger.error(f"Error searching chats: {e}")
            return False, []
    
    async def _search_and_select_chat(self, contact: str) -> Tuple[bool, str]:
        """Search for and select a specific chat"""
        try:
            # Search for the contact
            success, results = await self.search_chats(contact)
            if not success or not results:
                return False, f"Contact '{contact}' not found"
            
            # Click on the first result
            success, click_msg, _ = await self.browser.perform_action(
                'click',
                selector=f'[data-testid="search-result"]:first-child, ._2nY6U div:first-child'
            )
            
            if success:
                self.current_chat = contact
                return True, f"Selected chat with {contact}"
            else:
                return False, f"Failed to select chat: {click_msg}"
                
        except Exception as e:
            return False, str(e)
    
    def _extract_chat_name(self, chat_html: str) -> str:
        """Extract chat name from HTML (simplified)"""
        name_match = re.search(r'<span[^>]*title="([^"]+)"', chat_html)
        return name_match.group(1) if name_match else "Unknown Contact"
    
    def _extract_last_message(self, chat_html: str) -> str:
        """Extract last message preview from HTML (simplified)"""
        msg_match = re.search(r'<span[^>]*>([^<]{10,100})</span>', chat_html)
        message = msg_match.group(1) if msg_match else ""
        return message[:100] + "..." if len(message) > 100 else message
    
    def _extract_message_time(self, html: str) -> str:
        """Extract message time from HTML (simplified)"""
        time_match = re.search(r'(\d{1,2}:\d{2})', html)
        return time_match.group(1) if time_match else "Unknown"
    
    def _extract_unread_count(self, chat_html: str) -> int:
        """Extract unread message count from HTML (simplified)"""
        count_match = re.search(r'<span[^>]*>(\d+)</span>', chat_html)
        return int(count_match.group(1)) if count_match else 0
    
    def _is_group_chat(self, chat_html: str) -> bool:
        """Check if this is a group chat (simplified)"""
        return 'group' in chat_html.lower() or '👥' in chat_html
    
    def _extract_online_status(self, chat_html: str) -> str:
        """Extract online status (simplified)"""
        if 'online' in chat_html.lower():
            return 'online'
        elif 'last seen' in chat_html.lower():
            return 'offline'
        else:
            return 'unknown'
    
    def _extract_message_text(self, msg_html: str) -> str:
        """Extract message text from HTML (simplified)"""
        text_match = re.search(r'<span[^>]*>([^<]+)</span>', msg_html)
        return text_match.group(1) if text_match else ""
    
    def _extract_message_sender(self, msg_html: str) -> str:
        """Extract message sender from HTML (simplified)"""
        sender_match = re.search(r'data-sender="([^"]+)"', msg_html)
        return sender_match.group(1) if sender_match else "Unknown"
    
    def _is_outgoing_message(self, msg_html: str) -> bool:
        """Check if message is outgoing (simplified)"""
        return 'message-out' in msg_html or 'outgoing' in msg_html.lower()
    
    def _is_media_message(self, msg_html: str) -> bool:
        """Check if message contains media (simplified)"""
        media_indicators = ['image', 'video', 'audio', 'document', 'media']
        return any(indicator in msg_html.lower() for indicator in media_indicators)
    
    def _get_message_type(self, msg_html: str) -> str:
        """Get message type (text, image, video, etc.) (simplified)"""
        if 'image' in msg_html.lower():
            return 'image'
        elif 'video' in msg_html.lower():
            return 'video'
        elif 'audio' in msg_html.lower():
            return 'audio'
        elif 'document' in msg_html.lower():
            return 'document'
        else:
            return 'text'
    
    def _parse_search_results(self, results_html: str) -> List[Dict[str, Any]]:
        """Parse search results from HTML (simplified)"""
        results = []
        result_blocks = results_html.split('</div>')[:10]  # Limit to 10 results
        
        for i, block in enumerate(result_blocks):
            if not block.strip():
                continue
            
            try:
                result = {
                    'id': f"search_result_{i}",
                    'name': self._extract_chat_name(block),
                    'type': 'group' if self._is_group_chat(block) else 'contact',
                    'last_message': self._extract_last_message(block)
                }
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Failed to parse search result {i}: {e}")
                continue
        
        return results
    
    async def get_whatsapp_summary(self) -> Dict[str, Any]:
        """Get a summary of WhatsApp status"""
        try:
            if not self.authenticated:
                # Check authentication status
                auth_success, auth_message = await self.check_authentication_status()
                if not auth_success:
                    return {"error": "Not authenticated", "status": auth_message}
            
            # Get unread count
            success, unread_count = await self.get_unread_messages_count()
            
            # Get recent chats
            success_chats, recent_chats = await self.get_recent_chats(5)
            
            summary = {
                "authenticated": self.authenticated,
                "unread_count": unread_count if success else 0,
                "recent_chats_count": len(recent_chats) if success_chats else 0,
                "current_chat": self.current_chat,
                "recent_chats": recent_chats[:3] if success_chats else []  # Show first 3
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting WhatsApp summary: {e}")
            return {"error": str(e)}

def main():
    """Test WhatsApp service"""
    import asyncio
    from browser.playwright_manager import PlaywrightManager
    from security.permission_manager import PermissionManager
    from security.credential_vault import CredentialVault
    
    async def test_whatsapp():
        pm = PermissionManager()
        cv = CredentialVault()
        browser = PlaywrightManager(pm, cv)
        whatsapp = WhatsAppService(browser, pm)
        
        print("💬 Testing WhatsApp Service")
        print("=" * 40)
        
        # Start browser session
        success = await browser.start_browser_session()
        if not success:
            print("❌ Failed to start browser session")
            return
        
        # Test authentication
        success, message = await whatsapp.authenticate()
        print(f"Authentication: {success} - {message}")
        
        if "QR code" in message:
            print("📱 Scan QR code with your phone to continue testing...")
            
            # Wait a bit for potential authentication
            await asyncio.sleep(10)
            
            # Check authentication status
            auth_success, auth_message = await whatsapp.check_authentication_status()
            print(f"Auth Status: {auth_success} - {auth_message}")
            
            if auth_success:
                # Test getting summary
                summary = await whatsapp.get_whatsapp_summary()
                print(f"WhatsApp Summary: {summary}")
                
                # Test getting recent chats
                success, chats = await whatsapp.get_recent_chats(3)
                print(f"Recent Chats: {len(chats) if success else 0} chats retrieved")
        
        # Close browser session
        await browser.close_session()
    
    asyncio.run(test_whatsapp())

if __name__ == "__main__":
    main()
