#!/usr/bin/env python3
"""
Cleanup Duplicate System Categories
Removes duplicate system categories and updates transactions to use the correct ones
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(env_path)

# Connect to MongoDB
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'spendalizer')

try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    db = client[DB_NAME]
    print(f"✅ Connected to MongoDB: {MONGO_URL}")
    print(f"📊 Database: {DB_NAME}")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    print(f"   Make sure MongoDB is running and MONGO_URL is correct in backend/.env")
    sys.exit(1)

print("\n🔍 Checking for duplicate system categories...")

# Get all system categories
system_cats = list(db.categories.find({"is_system": True}))
print(f"Found {len(system_cats)} system categories in database")

# Group by name
by_name = defaultdict(list)
for cat in system_cats:
    by_name[cat['name']].append(cat)

# Find duplicates
duplicates = {name: cats for name, cats in by_name.items() if len(cats) > 1}

if not duplicates:
    print("\n✅ No duplicates found! Your database is clean.")
    client.close()
    sys.exit(0)

print(f"\n⚠️  Found {len(duplicates)} duplicate category names:")
print("=" * 70)

for name, cats in duplicates.items():
    print(f"\n📂 {name}: {len(cats)} entries")
    for cat in cats:
        txn_count = db.transactions.count_documents({"category_id": cat['id']})
        rule_count = db.category_rules.count_documents({"category_id": cat['id']})
        created = cat.get('created_at', 'unknown')[:10]  # Show date only
        print(f"   • ID: {cat['id'][:20]}... (created: {created}, {txn_count} txns, {rule_count} rules)")

print("\n" + "=" * 70)
print("⚠️  This script will:")
print("   1. Keep the NEWEST version of each category (by created_at)")
print("   2. Update all transactions to use the newest category ID")
print("   3. Update all rules to use the newest category ID")
print("   4. Delete the duplicate categories")
print("=" * 70)

response = input("\nDo you want to proceed with cleanup? (yes/no): ")

if response.lower() != 'yes':
    print("❌ Cleanup cancelled. No changes made.")
    client.close()
    sys.exit(0)

print("\n🧹 Starting cleanup...\n")

total_deleted = 0
total_txns_updated = 0
total_rules_updated = 0

for name, cats in duplicates.items():
    # Sort by created_at, keep the newest
    cats_sorted = sorted(cats, key=lambda x: x.get('created_at', '0000-00-00'), reverse=True)
    newest = cats_sorted[0]
    to_delete = cats_sorted[1:]
    
    print(f"📂 {name}:")
    print(f"   ✅ Keeping: {newest['id'][:20]}... (created: {newest.get('created_at', 'unknown')[:10]})")
    
    for cat in to_delete:
        # Update transactions
        txn_result = db.transactions.update_many(
            {"category_id": cat['id']},
            {"$set": {"category_id": newest['id']}}
        )
        
        # Update rules
        rule_result = db.category_rules.update_many(
            {"category_id": cat['id']},
            {"$set": {"category_id": newest['id']}}
        )
        
        if txn_result.modified_count > 0:
            print(f"   📝 Updated {txn_result.modified_count} transactions")
            total_txns_updated += txn_result.modified_count
        
        if rule_result.modified_count > 0:
            print(f"   📋 Updated {rule_result.modified_count} rules")
            total_rules_updated += rule_result.modified_count
        
        # Delete the duplicate category
        db.categories.delete_one({"_id": cat['_id']})
        print(f"   🗑️  Deleted: {cat['id'][:20]}...")
        total_deleted += 1

print("\n" + "=" * 70)
print("✅ Cleanup complete!")
print(f"   • Deleted {total_deleted} duplicate categories")
print(f"   • Updated {total_txns_updated} transactions")
print(f"   • Updated {total_rules_updated} rules")
print("=" * 70)

# Verify cleanup
remaining_system_cats = db.categories.count_documents({"is_system": True})
print(f"\n📊 Remaining system categories: {remaining_system_cats}")

# Check if there are still duplicates
remaining_dups = list(db.categories.aggregate([
    {"$match": {"is_system": True}},
    {"$group": {"_id": "$name", "count": {"$sum": 1}}},
    {"$match": {"count": {"$gt": 1}}}
]))

if remaining_dups:
    print(f"⚠️  Warning: Still {len(remaining_dups)} duplicates found!")
    for dup in remaining_dups:
        print(f"   • {dup['_id']}: {dup['count']} entries")
else:
    print("✅ No duplicates remaining!")

print("\n💡 Next steps:")
print("   1. Restart your backend: ./stop.sh && ./start.sh")
print("   2. Verify categories page shows 25 system categories with no duplicates")

client.close()
