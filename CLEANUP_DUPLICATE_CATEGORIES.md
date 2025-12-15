# Cleanup Duplicate System Categories

## Problem
Local database has duplicate system categories from before the fixed UUID implementation.

## Solution: Run Cleanup Script

### Option 1: Automated Cleanup (Recommended)

Run this Python script on your **LOCAL** machine:

```python
# cleanup_categories.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('backend/.env')

# Connect to local MongoDB
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'spendalizer')

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

print("🔍 Checking for duplicate system categories...")

# Get all system categories
system_cats = list(db.categories.find({"is_system": True}))
print(f"Found {len(system_cats)} system categories")

# Group by name
from collections import defaultdict
by_name = defaultdict(list)
for cat in system_cats:
    by_name[cat['name']].append(cat)

# Find duplicates
duplicates = {name: cats for name, cats in by_name.items() if len(cats) > 1}

if not duplicates:
    print("✅ No duplicates found!")
else:
    print(f"\n⚠️  Found {len(duplicates)} duplicate category names:")
    for name, cats in duplicates.items():
        print(f"\n  {name}: {len(cats)} entries")
        for cat in cats:
            print(f"    - ID: {cat['id'][:20]}... (created: {cat.get('created_at', 'unknown')})")
    
    # Ask for confirmation
    print("\n" + "="*60)
    response = input("Do you want to delete duplicates? (yes/no): ")
    
    if response.lower() == 'yes':
        total_deleted = 0
        for name, cats in duplicates.items():
            # Sort by created_at, keep the newest
            cats_sorted = sorted(cats, key=lambda x: x.get('created_at', ''), reverse=True)
            newest = cats_sorted[0]
            to_delete = cats_sorted[1:]
            
            print(f"\n{name}:")
            print(f"  Keeping: {newest['id'][:20]}... (created: {newest.get('created_at', 'unknown')})")
            
            for cat in to_delete:
                # Check if category is used by any transactions
                txn_count = db.transactions.count_documents({"category_id": cat['id']})
                if txn_count > 0:
                    print(f"  ⚠️  Skipping {cat['id'][:20]}... (used by {txn_count} transactions)")
                    # Update transactions to use the newest category
                    result = db.transactions.update_many(
                        {"category_id": cat['id']},
                        {"$set": {"category_id": newest['id']}}
                    )
                    print(f"     Updated {result.modified_count} transactions to use new category")
                
                # Delete the duplicate
                db.categories.delete_one({"_id": cat['_id']})
                print(f"  ✅ Deleted: {cat['id'][:20]}...")
                total_deleted += 1
        
        print(f"\n✅ Cleanup complete! Deleted {total_deleted} duplicate categories")
    else:
        print("❌ Cleanup cancelled")

client.close()
```

**Run it:**
```bash
cd /Users/ajay/Projects/spendalizer
python3 cleanup_categories.py
```

### Option 2: Manual MongoDB Commands

Run these commands in MongoDB shell:

```bash
# Connect to MongoDB
mongo spendalizer  # or your database name

# Check for duplicates
db.categories.aggregate([
  { $match: { is_system: true } },
  { $group: { 
      _id: "$name", 
      count: { $sum: 1 },
      ids: { $push: "$id" }
  }},
  { $match: { count: { $gt: 1 } }}
])

# Delete ALL system categories (if you want fresh start)
db.categories.deleteMany({ is_system: true })

# Then restart your backend - it will recreate with fixed UUIDs
```

### Option 3: Fresh Database (Nuclear Option)

If you don't have important data in local:

```bash
# Backup first (optional)
mongodump --db spendalizer --out /tmp/spendalizer_backup

# Drop database
mongo spendalizer --eval "db.dropDatabase()"

# Restart backend - will initialize fresh system categories
cd /Users/ajay/Projects/spendalizer
./stop.sh
./start.sh
```

## Prevention

After cleanup, the new code ensures:
- System categories use fixed UUIDs from `/app/backend/system_categories.json`
- Initialization checks by ID, won't create duplicates
- All environments have consistent category IDs

## Verification

After cleanup, verify:

```bash
# Count system categories (should be 25)
mongo spendalizer --eval "db.categories.find({is_system: true}).count()"

# Check for duplicates
mongo spendalizer --eval "db.categories.aggregate([
  { \$match: { is_system: true } },
  { \$group: { _id: '\$name', count: { \$sum: 1 }}},
  { \$match: { count: { \$gt: 1 }}}
])"
```

Should return 25 categories with no duplicates!
