#!/usr/bin/env python3
"""
Investigate the duplicate system category names issue
"""

import requests
import json
from datetime import datetime
from collections import Counter

def investigate_duplicates():
    base_url = "https://budget-buddy-3836.preview.emergentagent.com"
    
    # Register a new user
    test_user_data = {
        "email": f"investigate_{datetime.now().strftime('%H%M%S')}@example.com",
        "name": "Investigate User",
        "password": "TestPass123!"
    }
    
    response = requests.post(f"{base_url}/api/auth/register", json=test_user_data)
    if response.status_code != 200:
        print("❌ Failed to register user")
        return
    
    token = response.json()['token']
    headers = {'Authorization': f'Bearer {token}'}
    
    print(f"✅ Registered user")
    
    # Get all categories
    response = requests.get(f"{base_url}/api/categories", headers=headers)
    all_categories = response.json()
    
    system_categories = [cat for cat in all_categories if cat.get('is_system', False)]
    
    print(f"📊 Total system categories: {len(system_categories)}")
    
    # Check for duplicate names
    names = [cat['name'] for cat in system_categories]
    name_counts = Counter(names)
    
    duplicates = {name: count for name, count in name_counts.items() if count > 1}
    
    if duplicates:
        print(f"❌ Found {len(duplicates)} duplicate system category names:")
        for name, count in duplicates.items():
            print(f"   '{name}': {count} instances")
            
            # Show details of duplicates
            matching_cats = [cat for cat in system_categories if cat['name'] == name]
            for i, cat in enumerate(matching_cats):
                print(f"     Instance {i+1}: ID={cat['id'][:8]}..., type={cat.get('type')}, user_id={cat.get('user_id')}")
    else:
        print(f"✅ No duplicate system category names found")
    
    # Check IDs
    ids = [cat['id'] for cat in system_categories]
    id_counts = Counter(ids)
    
    id_duplicates = {id: count for id, count in id_counts.items() if count > 1}
    
    if id_duplicates:
        print(f"❌ Found {len(id_duplicates)} duplicate system category IDs:")
        for id, count in id_duplicates.items():
            print(f"   '{id}': {count} instances")
    else:
        print(f"✅ No duplicate system category IDs found")
    
    # Check system_categories.json file content
    print(f"\n🔍 Checking system_categories.json file...")
    
    with open('/app/backend/system_categories.json', 'r') as f:
        file_categories = json.load(f)
    
    file_names = [cat['name'] for cat in file_categories]
    file_name_counts = Counter(file_names)
    
    file_duplicates = {name: count for name, count in file_name_counts.items() if count > 1}
    
    if file_duplicates:
        print(f"❌ Found {len(file_duplicates)} duplicate names in system_categories.json:")
        for name, count in file_duplicates.items():
            print(f"   '{name}': {count} instances")
    else:
        print(f"✅ No duplicate names in system_categories.json")
    
    file_ids = [cat['id'] for cat in file_categories]
    file_id_counts = Counter(file_ids)
    
    file_id_duplicates = {id: count for id, count in file_id_counts.items() if count > 1}
    
    if file_id_duplicates:
        print(f"❌ Found {len(file_id_duplicates)} duplicate IDs in system_categories.json:")
        for id, count in file_id_duplicates.items():
            print(f"   '{id}': {count} instances")
    else:
        print(f"✅ No duplicate IDs in system_categories.json")
    
    print(f"\n📊 Comparison:")
    print(f"   File has {len(file_categories)} categories")
    print(f"   Database has {len(system_categories)} system categories")
    
    # Check if there are categories in DB that are not in file
    file_ids_set = set(file_ids)
    db_ids_set = set(ids)
    
    extra_in_db = db_ids_set - file_ids_set
    missing_in_db = file_ids_set - db_ids_set
    
    if extra_in_db:
        print(f"❌ Categories in DB but not in file: {len(extra_in_db)}")
        for id in list(extra_in_db)[:5]:  # Show first 5
            cat = next(cat for cat in system_categories if cat['id'] == id)
            print(f"   ID: {id[:8]}..., Name: '{cat['name']}'")
    
    if missing_in_db:
        print(f"❌ Categories in file but not in DB: {len(missing_in_db)}")
        for id in list(missing_in_db)[:5]:  # Show first 5
            cat = next(cat for cat in file_categories if cat['id'] == id)
            print(f"   ID: {id[:8]}..., Name: '{cat['name']}'")

if __name__ == "__main__":
    investigate_duplicates()