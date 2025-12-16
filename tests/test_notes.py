#!/usr/bin/env python3
"""
Test script for Notes tools
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add agent directory to path to import tools
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agent'))

from tools.notes import read_notes, update_notes
from aws_secrets import setup_credentials

async def test_update_notes_today():
    """Test updating notes for today"""
    print("✏️  Testing update_notes (today)...")
    
    try:
        result = await update_notes({
            'content': f'Test note added at {datetime.now().strftime("%H:%M:%S")}'
        })
        print(f"✅ Success: Updated notes for {result['date']}")
        
        return True, result['date']
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

async def test_read_notes_today():
    """Test reading notes for today"""
    print("\n📖 Testing read_notes (today)...")
    
    try:
        result = await read_notes({})
        print(f"✅ Success: Read notes for {result['date']}")
        print(f"   Content: {result['content'][:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_update_notes_specific_date():
    """Test updating notes for a specific date"""
    print("\n✏️  Testing update_notes (specific date)...")
    
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        result = await update_notes({
            'date': yesterday,
            'content': 'This is a test note for yesterday'
        })
        print(f"✅ Success: Updated notes for {result['date']}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_read_notes_specific_date():
    """Test reading notes for a specific date"""
    print("\n📖 Testing read_notes (specific date)...")
    
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        result = await read_notes({'date': yesterday})
        print(f"✅ Success: Read notes for {result['date']}")
        if result.get('content'):
            print(f"   Content: {result['content'][:100]}...")
        else:
            print(f"   {result.get('message', 'No content')}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Notes tool tests...\n")
    
    # Setup AWS credentials first
    setup_credentials()
    
    # Test update today
    update_today_success, _ = await test_update_notes_today()
    
    # Test read today
    read_today_success = await test_read_notes_today()
    
    # Test update specific date
    update_date_success = await test_update_notes_specific_date()
    
    # Test read specific date
    read_date_success = await test_read_notes_specific_date()
    
    print(f"\n📊 Test Results:")
    print(f"   Update Notes (today): {'✅ PASS' if update_today_success else '❌ FAIL'}")
    print(f"   Read Notes (today): {'✅ PASS' if read_today_success else '❌ FAIL'}")
    print(f"   Update Notes (specific date): {'✅ PASS' if update_date_success else '❌ FAIL'}")
    print(f"   Read Notes (specific date): {'✅ PASS' if read_date_success else '❌ FAIL'}")
    
    if all([update_today_success, read_today_success, update_date_success, read_date_success]):
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
