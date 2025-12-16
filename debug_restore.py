#!/usr/bin/env python3
"""
Debug script to investigate the system categories duplication issue
"""

import requests
import json
import tempfile
import os
from datetime import datetime
import zipfile
from io import BytesIO

def debug_categories_issue():
    base_url = "https://spendalizer.preview.emergentagent.com"
    
    # Register a new user
    test_user_data = {
        "email": f"debug_test_{datetime.now().strftime('%H%M%S')}@example.com",
        "name": "Debug Test User",
        "password": "TestPass123!"
    }
    
    response = requests.post(f"{base_url}/api/auth/register", json=test_user_data)
    if response.status_code != 200:
        print("❌ Failed to register user")
        return
    
    token = response.json()['token']
    user_id = response.json()['user']['id']
    headers = {'Authorization': f'Bearer {token}'}
    
    print(f"✅ Registered user: {user_id}")
    
    # Step 1: Check initial categories
    response = requests.get(f"{base_url}/api/categories", headers=headers)
    initial_categories = response.json()
    
    system_cats_initial = [cat for cat in initial_categories if cat.get('is_system', False)]
    user_cats_initial = [cat for cat in initial_categories if not cat.get('is_system', False)]
    
    print(f"📊 Initial state:")
    print(f"   System categories: {len(system_cats_initial)}")
    print(f"   User categories: {len(user_cats_initial)}")
    
    # Step 2: Create a user category
    user_cat_data = {"name": "Debug Test Category", "type": "EXPENSE"}
    response = requests.post(f"{base_url}/api/categories", json=user_cat_data, headers=headers)
    if response.status_code != 200:
        print("❌ Failed to create user category")
        return
    
    print(f"✅ Created user category")
    
    # Step 3: Check categories after creating user category
    response = requests.get(f"{base_url}/api/categories", headers=headers)
    after_create_categories = response.json()
    
    system_cats_after_create = [cat for cat in after_create_categories if cat.get('is_system', False)]
    user_cats_after_create = [cat for cat in after_create_categories if not cat.get('is_system', False)]
    
    print(f"📊 After creating user category:")
    print(f"   System categories: {len(system_cats_after_create)}")
    print(f"   User categories: {len(user_cats_after_create)}")
    
    # Step 4: Create backup
    response = requests.get(f"{base_url}/api/settings/backup", headers=headers)
    if response.status_code != 200:
        print("❌ Failed to create backup")
        return
    
    backup_data = response.content
    print(f"✅ Created backup")
    
    # Step 5: Examine backup contents
    zip_buffer = BytesIO(backup_data)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        categories_content = zip_file.read('categories.json')
        backup_categories = json.loads(categories_content)
    
    backup_system_cats = [cat for cat in backup_categories if cat.get('is_system', False)]
    backup_user_cats = [cat for cat in backup_categories if not cat.get('is_system', False)]
    
    print(f"📊 Backup contents:")
    print(f"   System categories in backup: {len(backup_system_cats)}")
    print(f"   User categories in backup: {len(backup_user_cats)}")
    
    # Step 6: Add another user category to modify state
    user_cat_data2 = {"name": "Debug Test Category 2", "type": "INCOME"}
    response = requests.post(f"{base_url}/api/categories", json=user_cat_data2, headers=headers)
    print(f"✅ Created second user category")
    
    # Step 7: Check categories before restore
    response = requests.get(f"{base_url}/api/categories", headers=headers)
    before_restore_categories = response.json()
    
    system_cats_before_restore = [cat for cat in before_restore_categories if cat.get('is_system', False)]
    user_cats_before_restore = [cat for cat in before_restore_categories if not cat.get('is_system', False)]
    
    print(f"📊 Before restore:")
    print(f"   System categories: {len(system_cats_before_restore)}")
    print(f"   User categories: {len(user_cats_before_restore)}")
    
    # Step 8: Restore backup
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        temp_file.write(backup_data)
        temp_file_path = temp_file.name
    
    with open(temp_file_path, 'rb') as f:
        files = {'file': ('backup.zip', f, 'application/zip')}
        response = requests.post(f"{base_url}/api/settings/restore", headers=headers, files=files)
    
    os.unlink(temp_file_path)
    
    if response.status_code != 200:
        print(f"❌ Restore failed: {response.status_code}")
        print(response.text)
        return
    
    restore_response = response.json()
    print(f"✅ Restore completed: {restore_response.get('restored_counts', {})}")
    
    # Step 9: Check categories after restore
    response = requests.get(f"{base_url}/api/categories", headers=headers)
    after_restore_categories = response.json()
    
    system_cats_after_restore = [cat for cat in after_restore_categories if cat.get('is_system', False)]
    user_cats_after_restore = [cat for cat in after_restore_categories if not cat.get('is_system', False)]
    
    print(f"📊 After restore:")
    print(f"   System categories: {len(system_cats_after_restore)}")
    print(f"   User categories: {len(user_cats_after_restore)}")
    
    # Step 10: Check for duplicates
    system_names = [cat['name'] for cat in system_cats_after_restore]
    system_ids = [cat['id'] for cat in system_cats_after_restore]
    
    duplicate_names = [name for name in set(system_names) if system_names.count(name) > 1]
    duplicate_ids = [id for id in set(system_ids) if system_ids.count(id) > 1]
    
    if duplicate_names:
        print(f"❌ DUPLICATE SYSTEM CATEGORY NAMES: {duplicate_names}")
    else:
        print(f"✅ No duplicate system category names")
    
    if duplicate_ids:
        print(f"❌ DUPLICATE SYSTEM CATEGORY IDS: {duplicate_ids}")
    else:
        print(f"✅ No duplicate system category IDs")
    
    # Step 11: Detailed analysis
    print(f"\n🔍 DETAILED ANALYSIS:")
    
    # Check if system categories from backup are being inserted
    for backup_sys_cat in backup_system_cats[:5]:  # Check first 5
        matching_cats = [cat for cat in after_restore_categories if cat['id'] == backup_sys_cat['id']]
        print(f"   System category '{backup_sys_cat['name']}' (ID: {backup_sys_cat['id'][:8]}...): {len(matching_cats)} instances")
        
        if len(matching_cats) > 1:
            print(f"     ❌ DUPLICATE FOUND!")
            for i, cat in enumerate(matching_cats):
                print(f"       Instance {i+1}: is_system={cat.get('is_system')}, user_id={cat.get('user_id')}")

if __name__ == "__main__":
    debug_categories_issue()