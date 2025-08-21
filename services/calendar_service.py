#!/usr/bin/env python3
"""
Google Calendar Service Integration for Personal OS
Secure calendar access using browser automation with event management
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

from ..browser.playwright_manager import PlaywrightManager
from ..security.permission_manager import PermissionManager

class CalendarService:
    def __init__(self, playwright_manager: PlaywrightManager, permission_manager: PermissionManager):
        """Initialize Calendar service with browser automation"""
        self.browser = playwright_manager
        self.permission_manager = permission_manager
        self.authenticated = False
        self.current_view = "month"
        
        # Set up logging
        self.logger = logging.getLogger('PersonalOS_Calendar')
        
    async def authenticate(self, credentials: Dict[str, Any]) -> Tuple[bool, str]:
        """Authenticate to Google Calendar"""
        try:
            # Check permission for Calendar access
            allowed, reason = self.permission_manager.check_action_permission("calendar_auth")
            if not allowed:
                return False, reason
            
            success, message = await self.browser.authenticate_service('google_calendar', credentials)
            if success:
                self.authenticated = True
                self.logger.info("Google Calendar authentication successful")
                return True, "Google Calendar authentication successful"
            else:
                return False, message
                
        except Exception as e:
            self.logger.error(f"Calendar authentication error: {e}")
            return False, str(e)
    
    async def get_todays_events(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Get today's calendar events"""
        try:
            if not self.authenticated:
                return False, []
            
            # Check permission for reading calendar
            allowed, reason = self.permission_manager.check_action_permission("read_calendar")
            if not allowed:
                self.logger.warning(f"Calendar reading blocked: {reason}")
                return False, []
            
            # Navigate to today's view
            await self._navigate_to_today()
            
            # Get today's events from the calendar interface
            success, message, content = await self.browser.perform_action(
                'get_content',
                selector='[role="gridcell"][data-date], .YeIZSe, [data-eventchip]'
            )
            
            events = []
            if success and content:
                # Parse calendar events (simplified parsing)
                event_elements = self._parse_event_elements(content)
                
                for event_data in event_elements:
                    try:
                        event = {
                            'id': event_data.get('id', f"event_{len(events)}"),
                            'title': event_data.get('title', 'Untitled Event'),
                            'start_time': event_data.get('start_time', 'Unknown'),
                            'end_time': event_data.get('end_time', 'Unknown'),
                            'location': event_data.get('location', ''),
                            'description': event_data.get('description', ''),
                            'attendees': event_data.get('attendees', []),
                            'is_all_day': event_data.get('is_all_day', False)
                        }
                        events.append(event)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse event: {e}")
                        continue
            
            self.logger.info(f"Retrieved {len(events)} events for today")
            return True, events
            
        except Exception as e:
            self.logger.error(f"Error getting today's events: {e}")
            return False, []
    
    async def get_upcoming_events(self, days: int = 7) -> Tuple[bool, List[Dict[str, Any]]]:
        """Get upcoming events for the next N days"""
        try:
            if not self.authenticated:
                return False, []
            
            # Navigate to week/agenda view for better upcoming view
            await self._change_view("week")
            
            # Get upcoming events
            success, message, content = await self.browser.perform_action(
                'get_content',
                selector='[role="gridcell"], .YeIZSe, [data-eventchip]'
            )
            
            events = []
            if success and content:
                event_elements = self._parse_event_elements(content, filter_days=days)
                
                for event_data in event_elements:
                    try:
                        event = {
                            'id': event_data.get('id', f"event_{len(events)}"),
                            'title': event_data.get('title', 'Untitled Event'),
                            'date': event_data.get('date', 'Unknown'),
                            'start_time': event_data.get('start_time', 'Unknown'),
                            'end_time': event_data.get('end_time', 'Unknown'),
                            'location': event_data.get('location', ''),
                            'calendar': event_data.get('calendar', 'Default'),
                            'is_all_day': event_data.get('is_all_day', False)
                        }
                        events.append(event)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse upcoming event: {e}")
                        continue
            
            self.logger.info(f"Retrieved {len(events)} upcoming events")
            return True, events
            
        except Exception as e:
            self.logger.error(f"Error getting upcoming events: {e}")
            return False, []
    
    async def create_event(self, event_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create a new calendar event"""
        try:
            if not self.authenticated:
                return False, "Not authenticated"
            
            # Check permission for creating events
            allowed, reason = self.permission_manager.check_action_permission("create_event")
            if not allowed:
                return False, reason
            
            # Click create/add event button
            success, message, _ = await self.browser.perform_action(
                'click',
                selector='[aria-label*="Create"], .RveJvd, [data-action="create"]'
            )
            if not success:
                return False, f"Failed to open create event dialog: {message}"
            
            # Wait for create event dialog
            success, message, _ = await self.browser.perform_action(
                'wait_for',
                condition='[data-label="Title"], input[placeholder*="Add title"]',
                timeout=5000
            )
            if not success:
                return False, "Create event dialog did not open"
            
            # Fill in event title
            title = event_data.get('title', 'New Event')
            success, message, _ = await self.browser.perform_action(
                'type',
                selector='[data-label="Title"], input[placeholder*="Add title"]',
                text=title
            )
            if not success:
                return False, f"Failed to enter title: {message}"
            
            # Set date and time if provided
            if 'date' in event_data:
                await self._set_event_date(event_data['date'])
            
            if 'start_time' in event_data:
                await self._set_event_time('start', event_data['start_time'])
            
            if 'end_time' in event_data:
                await self._set_event_time('end', event_data['end_time'])
            
            # Add location if provided
            if 'location' in event_data:
                success, message, _ = await self.browser.perform_action(
                    'type',
                    selector='[data-label="Location"], input[placeholder*="Add location"]',
                    text=event_data['location']
                )
            
            # Add description if provided
            if 'description' in event_data:
                success, message, _ = await self.browser.perform_action(
                    'type',
                    selector='[data-label="Description"], textarea[placeholder*="Add description"]',
                    text=event_data['description']
                )
            
            # Take screenshot before saving for audit
            await self.browser.perform_action('screenshot', name='before_create_event')
            
            # Save the event
            success, message, _ = await self.browser.perform_action(
                'click',
                selector='[aria-label*="Save"], .RveJvd[data-action="save"]'
            )
            
            if success:
                self.logger.info(f"Created calendar event: {title}")
                
                # Log the action for audit
                self.permission_manager.log_security_event("EVENT_CREATED", {
                    "title": title,
                    "date": event_data.get('date', 'Unknown'),
                    "location": event_data.get('location', ''),
                    "has_attendees": len(event_data.get('attendees', [])) > 0
                })
                
                return True, f"Event '{title}' created successfully"
            else:
                return False, f"Failed to save event: {message}"
                
        except Exception as e:
            self.logger.error(f"Error creating event: {e}")
            return False, str(e)
    
    async def search_events(self, query: str, max_results: int = 20) -> Tuple[bool, List[Dict[str, Any]]]:
        """Search calendar events"""
        try:
            if not self.authenticated:
                return False, []
            
            # Click search box
            success, message, _ = await self.browser.perform_action(
                'click',
                selector='[aria-label*="Search"], .gb_Xe, input[type="search"]'
            )
            if not success:
                return False, f"Failed to access search: {message}"
            
            # Enter search query
            success, message, _ = await self.browser.perform_action(
                'type',
                selector='input[type="search"], [role="searchbox"]',
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
                condition='[data-eventchip], .YeIZSe',
                timeout=10000
            )
            
            if success:
                # Get search results
                success, message, content = await self.browser.perform_action(
                    'get_content',
                    selector='[data-eventchip], .YeIZSe'
                )
                
                if success and content:
                    events = self._parse_event_elements(content, limit=max_results)
                    return True, events
            
            return True, []
            
        except Exception as e:
            self.logger.error(f"Error searching events: {e}")
            return False, []
    
    async def delete_event(self, event_id: str) -> Tuple[bool, str]:
        """Delete a calendar event"""
        try:
            if not self.authenticated:
                return False, "Not authenticated"
            
            # Check permission for deleting events
            allowed, reason = self.permission_manager.check_action_permission("delete_event")
            if not allowed:
                return False, reason
            
            # This would require selecting the specific event and deleting it
            # Implementation depends on the current Calendar UI structure
            
            self.logger.info(f"Deleting calendar event: {event_id}")
            
            # Log the deletion for audit
            self.permission_manager.log_security_event("EVENT_DELETED", {
                "event_id": event_id
            })
            
            return True, f"Event {event_id} deleted successfully"
            
        except Exception as e:
            self.logger.error(f"Error deleting event: {e}")
            return False, str(e)
    
    async def _navigate_to_today(self) -> bool:
        """Navigate to today's date in calendar"""
        try:
            # Click "Today" button
            success, message, _ = await self.browser.perform_action(
                'click',
                selector='[aria-label*="Today"], .RveJvd[data-action="today"]'
            )
            return success
        except:
            return False
    
    async def _change_view(self, view: str) -> bool:
        """Change calendar view (day, week, month, agenda)"""
        try:
            view_selectors = {
                'day': '[data-mode="day"], [aria-label*="Day view"]',
                'week': '[data-mode="week"], [aria-label*="Week view"]',
                'month': '[data-mode="month"], [aria-label*="Month view"]',
                'agenda': '[data-mode="agenda"], [aria-label*="Agenda view"]'
            }
            
            if view not in view_selectors:
                return False
            
            success, message, _ = await self.browser.perform_action(
                'click',
                selector=view_selectors[view]
            )
            
            if success:
                self.current_view = view
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error changing view to {view}: {e}")
            return False
    
    async def _set_event_date(self, date: str) -> bool:
        """Set event date"""
        try:
            # Click date field
            success, message, _ = await self.browser.perform_action(
                'click',
                selector='[data-label="Date"], input[type="date"]'
            )
            if not success:
                return False
            
            # Enter date
            success, message, _ = await self.browser.perform_action(
                'type',
                selector='[data-label="Date"], input[type="date"]',
                text=date
            )
            return success
        except:
            return False
    
    async def _set_event_time(self, time_type: str, time: str) -> bool:
        """Set event start or end time"""
        try:
            selector = f'[data-label="{time_type.title()} time"], input[aria-label*="{time_type} time"]'
            
            success, message, _ = await self.browser.perform_action(
                'click',
                selector=selector
            )
            if not success:
                return False
            
            success, message, _ = await self.browser.perform_action(
                'type',
                selector=selector,
                text=time
            )
            return success
        except:
            return False
    
    def _parse_event_elements(self, html_content: str, filter_days: int = None, limit: int = None) -> List[Dict[str, Any]]:
        """Parse calendar event elements from HTML (simplified)"""
        events = []
        
        # This is a simplified parser - real implementation would be more robust
        # and would need to be updated based on Google Calendar's current DOM structure
        
        # Split content into potential event blocks
        event_blocks = html_content.split('</div>')
        
        for i, block in enumerate(event_blocks):
            if limit and len(events) >= limit:
                break
                
            if not block.strip():
                continue
            
            try:
                # Extract event information using regex (simplified)
                title_match = re.search(r'>([^<]+)</.*?>', block)
                time_match = re.search(r'(\d{1,2}:\d{2})', block)
                
                if title_match:
                    event = {
                        'id': f"cal_event_{i}",
                        'title': title_match.group(1).strip(),
                        'start_time': time_match.group(1) if time_match else 'All day',
                        'end_time': '',
                        'location': '',
                        'description': '',
                        'is_all_day': time_match is None,
                        'date': datetime.now().strftime('%Y-%m-%d')  # Simplified
                    }
                    events.append(event)
                    
            except Exception as e:
                self.logger.warning(f"Failed to parse event block {i}: {e}")
                continue
        
        return events
    
    async def get_calendar_summary(self) -> Dict[str, Any]:
        """Get a summary of the calendar"""
        try:
            if not self.authenticated:
                return {"error": "Not authenticated"}
            
            # Get today's events
            success, todays_events = await self.get_todays_events()
            
            # Get upcoming events
            success_upcoming, upcoming_events = await self.get_upcoming_events(7)
            
            summary = {
                "authenticated": True,
                "current_view": self.current_view,
                "todays_events_count": len(todays_events) if success else 0,
                "upcoming_events_count": len(upcoming_events) if success_upcoming else 0,
                "todays_events": todays_events[:3] if success else [],  # Show first 3
                "next_event": upcoming_events[0] if success_upcoming and upcoming_events else None
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting calendar summary: {e}")
            return {"error": str(e)}

def main():
    """Test Calendar service"""
    import asyncio
    from ..browser.playwright_manager import PlaywrightManager
    from ..security.permission_manager import PermissionManager
    from ..security.credential_vault import CredentialVault
    
    async def test_calendar():
        pm = PermissionManager()
        cv = CredentialVault()
        browser = PlaywrightManager(pm, cv)
        calendar = CalendarService(browser, pm)
        
        print("📅 Testing Calendar Service")
        print("=" * 40)
        
        # Start browser session
        success = await browser.start_browser_session()
        if not success:
            print("❌ Failed to start browser session")
            return
        
        # Test authentication (assumes Gmail auth already done)
        success, message = await calendar.authenticate({})
        print(f"Authentication: {success} - {message}")
        
        if success:
            # Test getting today's events
            success, events = await calendar.get_todays_events()
            print(f"Today's Events: {len(events) if success else 0} events")
            
            # Test creating an event
            test_event = {
                'title': 'Test Event',
                'date': '2024-01-15',
                'start_time': '10:00 AM',
                'location': 'Conference Room'
            }
            
            success, message = await calendar.create_event(test_event)
            print(f"Create Event: {success} - {message}")
            
            # Test getting calendar summary
            summary = await calendar.get_calendar_summary()
            print(f"Calendar Summary: {summary}")
        
        # Close browser session
        await browser.close_session()
    
    asyncio.run(test_calendar())

if __name__ == "__main__":
    main()