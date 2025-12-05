#!/usr/bin/env python3

import requests
import json

def test_delete_validation():
    """Test the delete all validation logic"""
    
    base_url = "https://spend-tracker-140.preview.emergentagent.com"
    
    # First register a user
    import datetime
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    register_data = {
        "email": f"validation_test_{timestamp}@example.com",
        "name": "Validation Test User",
        "password": "TestPass123!"
    }
    
    response = requests.post(f"{base_url}/api/auth/register", json=register_data)
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.text}")
        return
    
    token = response.json()["token"]
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    print("✅ User registered successfully")
    
    # Test delete all with wrong confirmation (should fail with 400)
    print("\n🔍 Testing delete all with wrong confirmation...")
    delete_data = {"confirmation_text": "delete all"}  # lowercase
    
    response = requests.post(f"{base_url}/api/transactions/delete-all", json=delete_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 400:
        print("✅ Correctly rejected wrong confirmation")
    else:
        print("❌ Should have rejected wrong confirmation")
    
    # Test delete all with correct confirmation
    print("\n🔍 Testing delete all with correct confirmation...")
    delete_data = {"confirmation_text": "DELETE ALL"}  # uppercase
    
    response = requests.post(f"{base_url}/api/transactions/delete-all", json=delete_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Correctly accepted right confirmation")
    else:
        print("❌ Should have accepted correct confirmation")

if __name__ == "__main__":
    test_delete_validation()