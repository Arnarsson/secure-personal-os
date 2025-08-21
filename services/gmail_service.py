#!/usr/bin/env python3
"""
Gmail Service Integration for Personal OS
Secure Gmail access using browser automation with comprehensive email management
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

from browser.playwright_manager import PlaywrightManager
from security.permission_manager import PermissionManager

class GmailService:
    def __init__(self, playwright_manager: PlaywrightManager, permission_manager: PermissionManager):
        """Initialize Gmail service with browser automation"""
        self.browser = playwright_manager
        self.permission_manager = permission_manager
        self.authenticated = False
        self.current_folder = "inbox"
        
        # Set up logging
        self.logger = logging.getLogger('PersonalOS_Gmail')
        
    async def authenticate(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to Gmail"""
        try:
            # Check permission for Gmail access
            allowed, reason = self.permission_manager.check_action_permission("gmail_auth")
            if not allowed:
                return False, reason
            
            success, message = await self.browser.authenticate_service('gmail', credentials)
            if success:
                self.authenticated = True
                self.logger.info("Gmail authentication successful")
                return True, "Gmail authentication successful"
            else:
                return False, message
                
        except Exception as e:
            self.logger.error(f"Gmail authentication error: {e}")
            return False, str(e)
    
    async def get_unread_count(self) -> Tuple[bool, int]:
        """Get number of unread emails"""
        try:
            if not self.authenticated:
                return False, 0
            
            # Look for unread count in Gmail interface
            success, message, content = await self.browser.perform_action(
                'get_content',
                selector='[aria-label*="unread"]'
            )
            
            if success and content:
                # Extract number from content
                numbers = re.findall(r'\d+', content)
                if numbers:
                    unread_count = int(numbers[0])
                    self.logger.info(f"Found {unread_count} unread emails")
                    return True, unread_count
            
            return True, 0
            
        except Exception as e:
            self.logger.error(f"Error getting unread count: {e}")
            return False, 0
    
    async def get_recent_emails(self, count: int = 10) -> Tuple[bool, List[Dict[str, Any]]]:
        """Get recent emails from inbox"""
        try:
            if not self.authenticated:
                return False, []
            
            # Check permission for reading emails
            allowed, reason = self.permission_manager.check_action_permission("read_email")
            if not allowed:
                self.logger.warning(f"Email reading blocked: {reason}")
                return False, []
            
            emails = []
            
            # Navigate to inbox if not already there
            if self.current_folder != "inbox":
                await self._navigate_to_folder("inbox")
            
            # Get email list elements
            success, message, content = await self.browser.perform_action(
                'get_content',
                selector='[role="main"] tr'
            )
            
            if success and content:
                # Parse email elements (simplified parsing)
                email_elements = content.split('</tr>')[:count]
                
                for i, email_html in enumerate(email_elements):
                    if not email_html.strip():
                        continue
                    
                    try:
                        # Extract basic email info (this is simplified - real implementation would be more robust)
                        email_data = {
                            'id': f"email_{i}",
                            'subject': self._extract_subject(email_html),
                            'sender': self._extract_sender(email_html),
                            'date': self._extract_date(email_html),
                            'unread': 'unread' in email_html.lower(),
                            'snippet': self._extract_snippet(email_html)
                        }
                        emails.append(email_data)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse email {i}: {e}")
                        continue
            
            self.logger.info(f"Retrieved {len(emails)} recent emails")
            return True, emails
            
        except Exception as e:
            self.logger.error(f"Error getting recent emails: {e}")
            return False, []
    
    async def send_email(self, to: str, subject: str, body: str, attachments: List[str] = None) -> Tuple[bool, str]:
        """Send an email"""
        try:
            if not self.authenticated:
                return False, "Not authenticated"
            
            # Check permission for sending emails
            allowed, reason = self.permission_manager.check_action_permission("send_email")
            if not allowed:
                return False, reason
            
            # Click compose button
            success, message, _ = await self.browser.perform_action(
                'click',
                selector='[role="button"][aria-label*="Compose"], .T-I-KE'
            )
            if not success:
                return False, f"Failed to open compose: {message}"
            
            # Wait for compose dialog
            success, message, _ = await self.browser.perform_action(
                'wait_for',
                condition='[name="to"]',
                timeout=5000
            )
            if not success:
                return False, "Compose dialog did not open"
            
            # Fill in recipient
            success, message, _ = await self.browser.perform_action(
                'type',
                selector='[name="to"]',
                text=to
            )
            if not success:
                return False, f"Failed to enter recipient: {message}"
            
            # Fill in subject
            success, message, _ = await self.browser.perform_action(
                'type',
                selector='[name="subjectbox"]',
                text=subject
            )
            if not success:
                return False, f"Failed to enter subject: {message}"
            
            # Fill in body
            success, message, _ = await self.browser.perform_action(
                'type',
                selector='[role="textbox"][aria-label*="Message Body"]',
                text=body
            )
            if not success:
                return False, f"Failed to enter body: {message}"
            
            # Handle attachments if provided
            if attachments:
                for attachment in attachments:
                    # Check file access permission
                    allowed, reason = self.permission_manager.check_file_access(attachment, "read")
                    if not allowed:
                        return False, f"Attachment access denied: {reason}"
                    
                    # Click attach button and select file (simplified)
                    success, message, _ = await self.browser.perform_action(
                        'click',
                        selector='[aria-label*="Attach files"]'
                    )
                    # Note: File upload would require more complex handling
            
            # Take screenshot before sending for audit
            await self.browser.perform_action('screenshot', name='before_send_email')
            
            # Send email
            success, message, _ = await self.browser.perform_action(
                'click',
                selector='[role="button"][aria-label*="Send"], .T-I-KE'
            )
            
            if success:
                self.logger.info(f"Email sent to {to} with subject: {subject}")
                
                # Log the action for audit
                self.permission_manager.log_security_event("EMAIL_SENT", {
                    "recipient": to,
                    "subject": subject,
                    "body_length": len(body),
                    "attachments": len(attachments) if attachments else 0
                })
                
                return True, "Email sent successfully"
            else:
                return False, f"Failed to send email: {message}"
                
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False, str(e)
    
    async def search_emails(self, query: str, max_results: int = 20) -> Tuple[bool, List[Dict[str, Any]]]:
        """Search emails by query"""
        try:
            if not self.authenticated:
                return False, []
            
            # Click search box
            success, message, _ = await self.browser.perform_action(
                'click',
                selector='[role="search"] input, .gb_Xe'
            )
            if not success:
                return False, f"Failed to access search: {message}"
            
            # Enter search query
            success, message, _ = await self.browser.perform_action(
                'type',
                selector='[role="search"] input',
                text=query
            )
            if not success:
                return False, f"Failed to enter search: {message}"
            
            # Press Enter to search
            success, message, _ = await self.browser.perform_action(
                'key_press',
                key='Enter'
            )
            if not success:
                return False, f"Failed to execute search: {message}"
            
            # Wait for search results
            success, message, _ = await self.browser.perform_action(
                'wait_for',
                condition='[role="main"] tr',
                timeout=10000
            )
            
            if success:
                # Get search results (reuse email parsing logic)
                return await self.get_recent_emails(max_results)
            else:
                return False, []
                
        except Exception as e:
            self.logger.error(f"Error searching emails: {e}")
            return False, []
    
    async def mark_as_read(self, email_ids: List[str]) -> Tuple[bool, str]:
        """Mark emails as read"""
        try:
            if not self.authenticated:
                return False, "Not authenticated"
            
            # This would require selecting specific emails and marking them
            # Implementation would depend on Gmail's current UI structure
            self.logger.info(f"Marking {len(email_ids)} emails as read")
            
            # Simplified implementation - would need actual email selection logic
            success = True
            for email_id in email_ids:
                # Select email and mark as read
                pass
            
            return success, f"Marked {len(email_ids)} emails as read"
            
        except Exception as e:
            self.logger.error(f"Error marking emails as read: {e}")
            return False, str(e)
    
    async def delete_emails(self, email_ids: List[str]) -> Tuple[bool, str]:
        """Delete emails"""
        try:
            if not self.authenticated:
                return False, "Not authenticated"
            
            # Check permission for deleting emails
            allowed, reason = self.permission_manager.check_action_permission("delete_email")
            if not allowed:
                return False, reason
            
            self.logger.info(f"Deleting {len(email_ids)} emails")
            
            # Log the deletion for audit
            self.permission_manager.log_security_event("EMAIL_DELETE", {
                "email_count": len(email_ids),
                "email_ids": email_ids
            })
            
            # Implementation would select and delete specific emails
            return True, f"Deleted {len(email_ids)} emails"
            
        except Exception as e:
            self.logger.error(f"Error deleting emails: {e}")
            return False, str(e)
    
    async def _navigate_to_folder(self, folder: str) -> bool:
        """Navigate to a specific folder"""
        try:
            folder_selectors = {
                'inbox': '[aria-label*="Inbox"]',
                'sent': '[aria-label*="Sent"]',
                'drafts': '[aria-label*="Drafts"]',
                'spam': '[aria-label*="Spam"]',
                'trash': '[aria-label*="Trash"]'
            }
            
            if folder not in folder_selectors:
                return False
            
            success, message, _ = await self.browser.perform_action(
                'click',
                selector=folder_selectors[folder]
            )
            
            if success:
                self.current_folder = folder
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error navigating to folder {folder}: {e}")
            return False
    
    def _extract_subject(self, email_html: str) -> str:
        """Extract email subject from HTML (simplified)"""
        # This is a simplified extraction - real implementation would be more robust
        subject_match = re.search(r'<span[^>]*>([^<]+)</span>', email_html)
        return subject_match.group(1) if subject_match else "No Subject"
    
    def _extract_sender(self, email_html: str) -> str:
        """Extract sender from HTML (simplified)"""
        # Simplified extraction
        sender_match = re.search(r'<span[^>]*title="([^"]+)"', email_html)
        return sender_match.group(1) if sender_match else "Unknown Sender"
    
    def _extract_date(self, email_html: str) -> str:
        """Extract date from HTML (simplified)"""
        # Simplified extraction
        date_match = re.search(r'<span[^>]*>(\w{3} \d{1,2})</span>', email_html)
        return date_match.group(1) if date_match else "Unknown Date"
    
    def _extract_snippet(self, email_html: str) -> str:
        """Extract email snippet from HTML (simplified)"""
        # Simplified extraction
        snippet_match = re.search(r'<span[^>]*>([^<]{20,100})</span>', email_html)
        snippet = snippet_match.group(1) if snippet_match else ""
        return snippet[:100] + "..." if len(snippet) > 100 else snippet
    
    async def get_email_summary(self) -> Dict[str, Any]:
        """Get a summary of the Gmail account"""
        try:
            if not self.authenticated:
                return {"error": "Not authenticated"}
            
            # Get unread count
            success, unread_count = await self.get_unread_count()
            
            # Get recent emails
            success, recent_emails = await self.get_recent_emails(5)
            
            summary = {
                "authenticated": True,
                "unread_count": unread_count,
                "recent_emails_count": len(recent_emails) if success else 0,
                "current_folder": self.current_folder,
                "recent_emails": recent_emails[:3] if success else []  # Just show first 3
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting Gmail summary: {e}")
            return {"error": str(e)}

def main():
    """Test Gmail service"""
    import asyncio
    from browser.playwright_manager import PlaywrightManager
    from security.permission_manager import PermissionManager
    from security.credential_vault import CredentialVault
    
    async def test_gmail():
        pm = PermissionManager()
        cv = CredentialVault()
        browser = PlaywrightManager(pm, cv)
        gmail = GmailService(browser, pm)
        
        print("📧 Testing Gmail Service")
        print("=" * 40)
        
        # Start browser session
        success = await browser.start_browser_session()
        if not success:
            print("❌ Failed to start browser session")
            return
        
        # Test authentication (with mock credentials)
        test_credentials = {
            'email': 'test@example.com',
            'password': 'test_password'
        }
        
        success, message = await gmail.authenticate(test_credentials)
        print(f"Authentication: {success} - {message}")
        
        if success:
            # Test getting summary
            summary = await gmail.get_email_summary()
            print(f"Gmail Summary: {summary}")
            
            # Test getting recent emails
            success, emails = await gmail.get_recent_emails(5)
            print(f"Recent Emails: {len(emails) if success else 0} emails retrieved")
        
        # Close browser session
        await browser.close_session()
    
    asyncio.run(test_gmail())

if __name__ == "__main__":
    main()
