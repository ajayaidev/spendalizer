#!/usr/bin/env python3
"""
Fix duplicate system categories by removing old ones and keeping only the ones from system_categories.json
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

async def fix_duplicate_categories():
    ROOT_DIR = Path('/app/backend')
    load_dotenv(ROOT_DIR / '.env')
    
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🔧 Fixing duplicate system categories...")
    
    # Load the official system categories from JSON file
    with open('/app/backend/system_categories.json', 'r') as f:
        official_categories = json.load(f)
    
    official_ids = set(cat['id'] for cat in official_categories)
    print(f"📋 Official system categories: {len(official_categories)}")
    
    # Get all system categories from database
    db_categories = await db.categories.find({'is_system': True}, {'_id': 0}).to_list(1000)
    print(f"📊 System categories in DB: {len(db_categories)}")
    
    # Find categories that are NOT in the official list
    categories_to_remove = []
    categories_to_keep = []
    
    for cat in db_categories:
        if cat['id'] in official_ids:
            categories_to_keep.append(cat)
        else:
            categories_to_remove.append(cat)
    
    print(f"✅ Categories to keep: {len(categories_to_keep)}")
    print(f"❌ Categories to remove: {len(categories_to_remove)}")
    
    if categories_to_remove:
        print(f"\n🗑️  Removing old system categories:")
        for cat in categories_to_remove:
            print(f"   - {cat['name']} (ID: {cat['id'][:8]}..., created: {cat.get('created_at', 'N/A')})")
        
        # Remove old categories
        ids_to_remove = [cat['id'] for cat in categories_to_remove]
        result = await db.categories.delete_many({'id': {'$in': ids_to_remove}})
        print(f"✅ Removed {result.deleted_count} old system categories")
    
    # Verify the fix
    remaining_categories = await db.categories.find({'is_system': True}, {'_id': 0}).to_list(1000)
    print(f"\n📊 After cleanup:")
    print(f"   System categories remaining: {len(remaining_categories)}")
    
    # Check for duplicates
    from collections import Counter
    names = [cat['name'] for cat in remaining_categories]
    name_counts = Counter(names)
    duplicates = {name: count for name, count in name_counts.items() if count > 1}
    
    if duplicates:
        print(f"❌ Still have duplicates: {duplicates}")
    else:
        print(f"✅ No more duplicate system category names")
    
    # Check if all official categories are present
    remaining_ids = set(cat['id'] for cat in remaining_categories)
    missing_ids = official_ids - remaining_ids
    
    if missing_ids:
        print(f"❌ Missing official categories: {len(missing_ids)}")
        # Re-initialize missing categories
        for cat_data in official_categories:
            if cat_data['id'] in missing_ids:
                cat_data['created_at'] = datetime.now().isoformat()
                await db.categories.insert_one(cat_data)
                print(f"   + Added missing category: {cat_data['name']}")
    else:
        print(f"✅ All official categories are present")
    
    client.close()
    print(f"\n🎉 System categories cleanup completed!")

if __name__ == "__main__":
    asyncio.run(fix_duplicate_categories())