#!/usr/bin/env python3
"""
Script to remove loan-related system categories from the database.
This is needed because the backend startup logic doesn't delete categories
that were removed from system_categories.json.
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

# Categories to delete (IDs from the original system_categories.json)
CATEGORIES_TO_DELETE = [
    # From INCOME
    "2d9f50c2-4a06-4d7a-8092-db6eedb6b3f1",  # Loan Received
    "92481d97-3308-4be1-8d81-ce8f20953050",  # Loan Repayment Received
    
    # From EXPENSE
    "7f8e9a7d-9b7c-4e8d-5f6a-3b8c9d7e8f9a",  # Loan Given
    "6a9f8b8e-8c6d-4f9e-4a5b-2c9d8e7f8a9b",  # Loan Repayment Made
]

async def cleanup_loan_categories():
    # Connect to MongoDB
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🔍 Checking for loan-related categories to delete...")
    
    # Find all categories to be deleted
    categories = await db.categories.find(
        {"id": {"$in": CATEGORIES_TO_DELETE}},
        {"_id": 0}
    ).to_list(100)
    
    print(f"\n📋 Found {len(categories)} categories to delete:")
    for cat in categories:
        print(f"  - {cat['name']} ({cat['type']}) [ID: {cat['id']}]")
    
    if not categories:
        print("\n✅ No loan categories found in database. Already cleaned up!")
        return
    
    # Check if any transactions are using these categories
    print("\n🔍 Checking for transactions using these categories...")
    for cat_id in CATEGORIES_TO_DELETE:
        txn_count = await db.transactions.count_documents({"category_id": cat_id})
        if txn_count > 0:
            cat = next((c for c in categories if c['id'] == cat_id), None)
            cat_name = cat['name'] if cat else "Unknown"
            print(f"  ⚠️  {txn_count} transaction(s) using category '{cat_name}'")
    
    # Delete the categories
    result = await db.categories.delete_many(
        {"id": {"$in": CATEGORIES_TO_DELETE}}
    )
    
    print(f"\n✅ Deleted {result.deleted_count} loan-related categories from database")
    
    # Also check for the "Refunds/Reimbursements" category and ensure it has the right type
    refund_cat = await db.categories.find_one(
        {"id": "d5221882-05a4-4540-aa04-64f595253d16"},
        {"_id": 0}
    )
    
    if refund_cat:
        if refund_cat['type'] != 'TRANSFER_EXTERNAL_IN':
            print(f"\n🔄 Updating 'Refunds/Reimbursements' type from {refund_cat['type']} to TRANSFER_EXTERNAL_IN")
            await db.categories.update_one(
                {"id": "d5221882-05a4-4540-aa04-64f595253d16"},
                {"$set": {"type": "TRANSFER_EXTERNAL_IN"}}
            )
            print("✅ Updated Refunds/Reimbursements category type")
        else:
            print(f"\n✅ 'Refunds/Reimbursements' already has correct type: TRANSFER_EXTERNAL_IN")
    
    print("\n🎉 Cleanup complete!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_loan_categories())
