#!/usr/bin/env python3
"""
Migrate legacy TRANSFER_EXTERNAL and TRANSFER_INTERNAL categories 
to explicit IN/OUT types for better organization
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

async def migrate_categories():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🔍 Finding categories with legacy transfer types...\n")
    
    # Find all categories with legacy types
    legacy_external = await db.categories.find(
        {"type": "TRANSFER_EXTERNAL"},
        {"_id": 0}
    ).to_list(1000)
    
    legacy_internal = await db.categories.find(
        {"type": "TRANSFER_INTERNAL"},
        {"_id": 0}
    ).to_list(1000)
    
    print(f"Found {len(legacy_external)} categories with TRANSFER_EXTERNAL")
    print(f"Found {len(legacy_internal)} categories with TRANSFER_INTERNAL\n")
    
    if not legacy_external and not legacy_internal:
        print("✅ No legacy categories found. All categories are already using explicit types!")
        client.close()
        return
    
    # Show what will be updated
    print("📋 Categories to be updated:\n")
    
    print("TRANSFER_EXTERNAL → TRANSFER_EXTERNAL_OUT:")
    for cat in legacy_external:
        is_system = "🔒 System" if cat.get('is_system') else "👤 Custom"
        print(f"  - {cat['name']:<40} {is_system}")
    
    if legacy_internal:
        print("\nTRANSFER_INTERNAL → TRANSFER_INTERNAL_OUT:")
        for cat in legacy_internal:
            is_system = "🔒 System" if cat.get('is_system') else "👤 Custom"
            print(f"  - {cat['name']:<40} {is_system}")
    
    print("\n" + "="*60)
    response = input("\nProceed with migration? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Migration cancelled")
        client.close()
        return
    
    # Perform migration
    print("\n🔄 Migrating categories...\n")
    
    # Update TRANSFER_EXTERNAL → TRANSFER_EXTERNAL_OUT
    if legacy_external:
        result = await db.categories.update_many(
            {"type": "TRANSFER_EXTERNAL"},
            {"$set": {"type": "TRANSFER_EXTERNAL_OUT"}}
        )
        print(f"✅ Updated {result.modified_count} TRANSFER_EXTERNAL categories to TRANSFER_EXTERNAL_OUT")
    
    # Update TRANSFER_INTERNAL → TRANSFER_INTERNAL_OUT
    if legacy_internal:
        result = await db.categories.update_many(
            {"type": "TRANSFER_INTERNAL"},
            {"$set": {"type": "TRANSFER_INTERNAL_OUT"}}
        )
        print(f"✅ Updated {result.modified_count} TRANSFER_INTERNAL categories to TRANSFER_INTERNAL_OUT")
    
    print("\n🎉 Migration complete!")
    print("\nNote: If these should be TRANSFER_EXTERNAL_IN or TRANSFER_INTERNAL_IN instead,")
    print("you can manually change them from the Categories page in the app.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_categories())
