#!/usr/bin/env python3
"""
Test script for Google Calendar tools
"""
import asyncio
import sys
import os

# Add agent directory to path to import tools
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agent'))

from tools.google_calendar import list_calendar_events, create_calendar_event
from aws_secrets import setup_credentials

async def test_list_events():
    """Test listing calendar events"""
    print("🔍 Testing list_calendar_events...")
    
    try:
        # Test with default parameters (next 10 events)
        result = await list_calendar_events({})
        print(f"✅ Success: Found {len(result.get('events', []))} events")
        
        for i, event in enumerate(result.get('events', [])[:3]):  # Show first 3
            print(f"  {i+1}. {event['title']} - {event['start']}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_create_event():
    """Test creating a calendar event"""
    print("\n📅 Testing create_calendar_event...")
    
    try:
        from datetime import datetime, timedelta
        
        # Create event for 1 hour from now
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        event_data = {
            "title": "Test Event from Nova Sonic",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "description": "This is a test event created by the calendar tool"
        }
        
        result = await create_calendar_event(event_data)
        print(f"✅ Success: Created event {result['event_id']}")
        print(f"   Link: {result['link']}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Google Calendar tool tests...\n")
    
    # Setup AWS credentials first
    setup_credentials()
    
    # Test list events
    list_success = await test_list_events()
    
    # Test create event
    create_success = await test_create_event()
    
    print(f"\n📊 Test Results:")
    print(f"   List Events: {'✅ PASS' if list_success else '❌ FAIL'}")
    print(f"   Create Event: {'✅ PASS' if create_success else '❌ FAIL'}")
    
    if list_success and create_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
