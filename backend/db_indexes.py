"""
Database indexes for performance optimization
Run this script to create indexes on frequently queried fields
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def create_indexes():
    """Create database indexes for better query performance"""
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("Creating database indexes...")
    
    # Users collection
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    print("✅ Users indexes created")
    
    # Transactions collection (most critical for performance)
    await db.transactions.create_index([("user_id", 1), ("date", -1)])  # Compound index for filtering and sorting
    await db.transactions.create_index([("user_id", 1), ("category_id", 1)])  # For category lookups
    await db.transactions.create_index([("user_id", 1), ("account_id", 1)])  # For account filtering
    await db.transactions.create_index("id", unique=True)
    print("✅ Transactions indexes created")
    
    # Categories collection
    await db.categories.create_index([("user_id", 1), ("type", 1)])  # Filter by user and type
    await db.categories.create_index([("is_system", 1), ("type", 1)])  # System categories lookup
    await db.categories.create_index("id", unique=True)
    print("✅ Categories indexes created")
    
    # Accounts collection
    await db.accounts.create_index([("user_id", 1)])
    await db.accounts.create_index("id", unique=True)
    print("✅ Accounts indexes created")
    
    # Rules collection
    await db.rules.create_index([("user_id", 1), ("priority", -1)])  # Sort by priority
    await db.rules.create_index("id", unique=True)
    print("✅ Rules indexes created")
    
    # Import batches collection
    await db.import_batches.create_index([("user_id", 1), ("imported_at", -1)])
    await db.import_batches.create_index("id", unique=True)
    print("✅ Import batches indexes created")
    
    print("\n🎉 All indexes created successfully!")
    print("\nExisting indexes:")
    for collection_name in ['users', 'transactions', 'categories', 'accounts', 'rules']:
        indexes = await db[collection_name].index_information()
        print(f"\n{collection_name}:")
        for idx_name, idx_info in indexes.items():
            print(f"  - {idx_name}: {idx_info.get('key', [])}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())
