#!/usr/bin/env python3
"""
Check categories in database to debug missing categories in Trend Report
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

async def check_categories():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("Checking categories with 'Loan' or 'Investment' in name...\n")
    
    # Find all categories with these keywords
    categories = await db.categories.find(
        {"name": {"$regex": "Loan|Investment|WINTWEALTH|ZERODHA|MF SIP", "$options": "i"}},
        {"_id": 0}
    ).to_list(100)
    
    if not categories:
        print("❌ No matching categories found!")
        return
    
    print(f"Found {len(categories)} matching categories:\n")
    
    # Group by type
    by_type = {}
    for cat in categories:
        cat_type = cat.get('type', 'NO_TYPE')
        if cat_type not in by_type:
            by_type[cat_type] = []
        by_type[cat_type].append(cat)
    
    # Display
    for cat_type, cats in sorted(by_type.items()):
        print(f"📊 {cat_type}:")
        for cat in cats:
            is_system = "🔒 System" if cat.get('is_system') else "👤 Custom"
            user_id = cat.get('user_id', 'N/A')[:8] if cat.get('user_id') else 'N/A'
            print(f"  - {cat['name']:<35} {is_system}  User: {user_id}  ID: {cat['id'][:13]}...")
        print()
    
    # Check if any categories have transactions
    print("\nChecking transaction counts for these categories...\n")
    for cat in categories:
        txn_count = await db.transactions.count_documents({"category_id": cat['id']})
        if txn_count > 0:
            print(f"  {cat['name']:<35} {txn_count} transactions")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_categories())
