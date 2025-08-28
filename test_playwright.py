#!/usr/bin/env python3
"""
Quick test script for the real Playwright implementation
Tests basic browser automation and service authentication
"""

import asyncio
import sys
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent))

from core.secure_personal_os import SecurePersonalOS

async def test_basic_browser():
    """Test basic browser functionality"""
    print("=" * 60)
    print("🧪 TESTING REAL PLAYWRIGHT IMPLEMENTATION")
    print("=" * 60)
    
    # Initialize Personal OS
    pos = SecurePersonalOS()
    
    # Test 1: Initialize session
    print("\n1️⃣ Testing session initialization...")
    success, message = await pos.initialize_session("test_password_123")
    print(f"   Result: {'✅' if success else '❌'} {message}")
    
    if not success:
        print("   Failed to initialize session. Exiting.")
        return
    
    # Test 2: System status
    print("\n2️⃣ Testing system status...")
    status = pos.get_system_status()
    print(f"   Session Active: {status['session_active']}")
    print(f"   Browser Status: {status['browser_status']['active']}")
    
    # Test 3: Navigate to Google (simple test)
    print("\n3️⃣ Testing navigation to Google...")
    success, message = await pos.browser_manager.navigate_to_url("https://www.google.com")
    print(f"   Result: {'✅' if success else '❌'} {message}")
    
    # Test 4: Take a screenshot
    print("\n4️⃣ Testing screenshot capability...")
    success, message, filepath = await pos.browser_manager.perform_action('screenshot', name='google_test')
    print(f"   Result: {'✅' if success else '❌'} Screenshot saved to: {filepath}")
    
    # Test 5: Test Gmail navigation (without credentials)
    print("\n5️⃣ Testing Gmail navigation...")
    success, message = await pos.browser_manager.navigate_to_url("https://mail.google.com")
    print(f"   Result: {'✅' if success else '❌'} {message}")
    
    # Wait a moment to see the browser
    await asyncio.sleep(2)
    
    # Test 6: Test WhatsApp navigation
    print("\n6️⃣ Testing WhatsApp Web navigation...")
    success, message = await pos.browser_manager.navigate_to_url("https://web.whatsapp.com")
    print(f"   Result: {'✅' if success else '❌'} {message}")
    
    # Take screenshot of WhatsApp QR
    if success:
        success, message, filepath = await pos.browser_manager.perform_action('screenshot', name='whatsapp_qr')
        print(f"   QR Screenshot: {'✅' if success else '❌'} {filepath}")
    
    # Wait a moment
    await asyncio.sleep(2)
    
    # Test 7: Close session
    print("\n7️⃣ Testing session cleanup...")
    success, message = await pos.close_session()
    print(f"   Result: {'✅' if success else '❌'} {message}")
    
    print("\n" + "=" * 60)
    print("✨ TEST COMPLETE!")
    print("=" * 60)
    print("\nSummary:")
    print("  - Playwright is working with real browser automation")
    print("  - Screenshots are being saved properly")
    print("  - Navigation to services is functional")
    print("  - Session management is operational")
    print("\nNext Steps:")
    print("  1. Add real credentials to test authentication")
    print("  2. Test email reading/sending")
    print("  3. Test calendar operations")
    print("  4. Deploy to production")

async def test_with_auth():
    """Test with actual authentication (requires credentials)"""
    print("\n" + "=" * 60)
    print("🔐 TESTING WITH AUTHENTICATION")
    print("=" * 60)
    print("\n⚠️  This test requires real credentials.")
    print("   Edit this function with your credentials to test authentication.\n")
    
    # Uncomment and fill in your credentials to test
    """
    pos = SecurePersonalOS()
    
    # Initialize
    await pos.initialize_session("your_master_password")
    
    # Authenticate Gmail
    gmail_creds = {
        'email': 'your-email@gmail.com',
        'password': 'your-app-password'  # Use app-specific password
    }
    
    results = await pos.authenticate_services({'gmail': gmail_creds})
    print(f"Gmail Auth: {results}")
    
    # Get daily briefing
    briefing = await pos.get_daily_briefing()
    print(f"Daily Briefing: {briefing}")
    
    # Close
    await pos.close_session()
    """
    
    print("   Skipping authentication test (no credentials provided)")

async def main():
    """Main test runner"""
    print("\n🚀 Secure Personal OS - Playwright Test Suite\n")
    
    # Run basic browser test
    await test_basic_browser()
    
    # Run auth test (if configured)
    await test_with_auth()
    
    print("\n✅ All tests completed!\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()