#!/usr/bin/env python3
"""
Test script for Gmail MCP Server
Tests basic Gmail functionality
"""

from gmail_client import GmailClient

def test_gmail_connection():
    """Test Gmail connection and basic operations."""
    print("🔍 Testing Gmail Connection...")
    print("-" * 50)
    
    try:
        # Initialize client
        print("1. Initializing Gmail client...")
        client = GmailClient()
        print("   ✅ Gmail client initialized successfully!")
        
        # Test 1: Get unread emails
        print("\n2. Testing: Get unread emails...")
        unread_emails = client.get_unread_emails(max_results=5)
        print(f"   ✅ Found {len(unread_emails)} unread email(s)")
        
        if unread_emails:
            print(f"\n   📧 Sample email IDs:")
            for i, email in enumerate(unread_emails[:3], 1):
                print(f"      {i}. {email['id']}")
        
        # Test 2: Get email details (if we have emails)
        if unread_emails:
            print("\n3. Testing: Get email details...")
            first_email_id = unread_emails[0]['id']
            email_details = client.get_email_details(first_email_id)
            print(f"   ✅ Retrieved email details")
            print(f"   📨 Subject: {email_details.get('headers', {}).get('subject', 'N/A')}")
            print(f"   👤 From: {email_details.get('headers', {}).get('from', 'N/A')}")
            print(f"   📝 Snippet: {email_details.get('snippet', 'N/A')[:100]}...")
        
        # Test 3: List emails with query
        print("\n4. Testing: List emails with search query...")
        recent_emails = client.list_emails(query="", max_results=3)
        print(f"   ✅ Found {len(recent_emails)} recent email(s)")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! Gmail MCP Server is working!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n" + "=" * 50)
        print("❌ Test failed. Please check your configuration.")
        print("=" * 50)
        return False

if __name__ == "__main__":
    test_gmail_connection()
