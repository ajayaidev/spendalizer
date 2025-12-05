#!/usr/bin/env python3

import requests
import json
import datetime

def debug_delete_test():
    """Debug the delete all validation"""
    
    base_url = "https://spend-tracker-140.preview.emergentagent.com"
    
    # Register a new user
    timestamp = datetime.datetime.now().strftime("%H%M%S%f")
    register_data = {
        "email": f"debug_test_{timestamp}@example.com",
        "name": "Debug Test User",
        "password": "TestPass123!"
    }
    
    print(f"🔍 Registering user: {register_data['email']}")
    response = requests.post(f"{base_url}/api/auth/register", json=register_data)
    print(f"Registration status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.text}")
        return
    
    token = response.json()["token"]
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    print("✅ User registered successfully")
    
    # Test various confirmation texts
    test_cases = [
        ("delete all", "Should be rejected (lowercase)"),
        ("Delete All", "Should be rejected (mixed case)"),
        ("DELETE ALL", "Should be accepted (uppercase)"),
        ("DELETE_ALL", "Should be rejected (underscore)"),
        ("delete", "Should be rejected (partial)"),
        ("", "Should be rejected (empty)"),
        ("  DELETE ALL  ", "Should be accepted (with spaces)"),
    ]
    
    for confirmation_text, description in test_cases:
        print(f"\n🔍 Testing: '{confirmation_text}' - {description}")
        
        delete_data = {"confirmation_text": confirmation_text}
        
        response = requests.post(f"{base_url}/api/transactions/delete-all", json=delete_data, headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        expected_status = 200 if confirmation_text.strip().upper() == "DELETE ALL" else 400
        if response.status_code == expected_status:
            print(f"   ✅ Correct behavior")
        else:
            print(f"   ❌ Expected {expected_status}, got {response.status_code}")

if __name__ == "__main__":
    debug_delete_test()