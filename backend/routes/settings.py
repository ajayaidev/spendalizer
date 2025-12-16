"""Settings routes (backup, restore, data management)."""
import os
import json
import logging
import zipfile
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse

from database import db
from auth import get_current_user
from models.schemas import DeleteAllTransactionsRequest

router = APIRouter(tags=["settings"])


@router.post("/transactions/delete-all")
async def delete_all_transactions(
    request: DeleteAllTransactionsRequest,
    user_id: str = Depends(get_current_user)
):
    if request.confirmation_text.strip().upper() != "DELETE ALL":
        raise HTTPException(status_code=400, detail="Confirmation text does not match. Please type 'DELETE ALL'")
    
    if not any([request.delete_transactions, request.delete_categories, request.delete_rules,
                request.delete_accounts, request.delete_imports]):
        raise HTTPException(status_code=400, detail="Please select at least one data type to delete")
    
    deletion_results = {
        "transactions": 0, "categories": 0, "rules": 0,
        "accounts": 0, "import_batches": 0
    }
    
    if request.delete_transactions:
        result = await db.transactions.delete_many({"user_id": user_id})
        deletion_results["transactions"] = result.deleted_count
        logging.warning(f"User {user_id} deleted {result.deleted_count} transactions")
    
    if request.delete_categories:
        result = await db.categories.delete_many({"user_id": user_id})
        deletion_results["categories"] = result.deleted_count
        logging.warning(f"User {user_id} deleted {result.deleted_count} custom categories")
    
    if request.delete_rules:
        result = await db.category_rules.delete_many({"user_id": user_id})
        deletion_results["rules"] = result.deleted_count
        logging.warning(f"User {user_id} deleted {result.deleted_count} rules")
    
    if request.delete_accounts:
        result = await db.accounts.delete_many({"user_id": user_id})
        deletion_results["accounts"] = result.deleted_count
        logging.warning(f"User {user_id} deleted {result.deleted_count} accounts")
    
    if request.delete_imports:
        result = await db.import_batches.delete_many({"user_id": user_id})
        deletion_results["import_batches"] = result.deleted_count
        logging.warning(f"User {user_id} deleted {result.deleted_count} import batches")
    
    deleted_items = [f"{count} {name}" for name, count in deletion_results.items() if count > 0]
    message = f"Successfully deleted: {', '.join(deleted_items)}"
    
    return {"message": message, "deletion_results": deletion_results}


@router.get("/debug/data-check")
async def debug_data_check(user_id: str = Depends(get_current_user)):
    transactions = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(10000)
    categories = await db.categories.find(
        {"$or": [{"is_system": True}, {"user_id": user_id}]},
        {"_id": 0}
    ).to_list(1000)
    
    txn_category_ids = set(txn.get("category_id") for txn in transactions if txn.get("category_id"))
    available_category_ids = set(cat["id"] for cat in categories)
    orphaned_category_ids = txn_category_ids - available_category_ids
    
    categorized_count = sum(1 for txn in transactions if txn.get("category_id"))
    uncategorized_count = len(transactions) - categorized_count
    
    return {
        "total_transactions": len(transactions),
        "categorized_transactions": categorized_count,
        "uncategorized_transactions": uncategorized_count,
        "total_categories": len(categories),
        "system_categories": sum(1 for cat in categories if cat.get("is_system")),
        "user_categories": sum(1 for cat in categories if cat.get("user_id")),
        "unique_category_ids_in_transactions": len(txn_category_ids),
        "orphaned_category_ids": list(orphaned_category_ids),
        "orphaned_count": len(orphaned_category_ids),
        "status": "OK" if len(orphaned_category_ids) == 0 else "WARNING: Orphaned categories found"
    }


@router.get("/settings/backup")
async def backup_database(user_id: str = Depends(get_current_user)):
    try:
        transactions = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(10000)
        categories = await db.categories.find(
            {"$or": [{"is_system": True}, {"user_id": user_id}]},
            {"_id": 0}
        ).to_list(1000)
        rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        accounts = await db.accounts.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        import_batches = await db.import_batches.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('transactions.json', json.dumps(transactions, indent=2, default=str))
            zip_file.writestr('categories.json', json.dumps(categories, indent=2, default=str))
            zip_file.writestr('rules.json', json.dumps(rules, indent=2, default=str))
            zip_file.writestr('accounts.json', json.dumps(accounts, indent=2, default=str))
            zip_file.writestr('import_batches.json', json.dumps(import_batches, indent=2, default=str))
            
            metadata = {
                "backup_date": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "app_version": "1.0.0",
                "collections": {
                    "transactions": len(transactions),
                    "categories": len(categories),
                    "rules": len(rules),
                    "accounts": len(accounts),
                    "import_batches": len(import_batches)
                }
            }
            zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
        
        zip_buffer.seek(0)
        
        domain = os.environ.get('DOMAIN', 'localhost')
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"SpendAlizer-{domain}-{timestamp}.zip"
        
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Backup failed for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.post("/settings/restore")
async def restore_database(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    try:
        logging.info(f"Creating pre-restore backup for user {user_id}")
        current_transactions = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(10000)
        current_categories = await db.categories.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        current_rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        current_accounts = await db.accounts.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        current_imports = await db.import_batches.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        
        pre_restore_buffer = BytesIO()
        with zipfile.ZipFile(pre_restore_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('transactions.json', json.dumps(current_transactions, indent=2, default=str))
            zip_file.writestr('categories.json', json.dumps(current_categories, indent=2, default=str))
            zip_file.writestr('rules.json', json.dumps(current_rules, indent=2, default=str))
            zip_file.writestr('accounts.json', json.dumps(current_accounts, indent=2, default=str))
            zip_file.writestr('import_batches.json', json.dumps(current_imports, indent=2, default=str))
            metadata = {"backup_date": datetime.now(timezone.utc).isoformat(), "backup_type": "pre_restore", "user_id": user_id}
            zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
        
        backup_dir = Path("/tmp/spendalizer_backups")
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = backup_dir / f"pre_restore_{user_id}_{timestamp}.zip"
        with open(backup_path, 'wb') as f:
            f.write(pre_restore_buffer.getvalue())
        
        content = await file.read()
        zip_buffer = BytesIO(content)
        
        try:
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                required_files = ['transactions.json', 'categories.json', 'rules.json', 'accounts.json', 'metadata.json']
                zip_files = zip_file.namelist()
                
                for req_file in required_files:
                    if req_file not in zip_files:
                        raise HTTPException(status_code=400, detail=f"Invalid backup file: missing {req_file}")
                
                metadata = json.loads(zip_file.read('metadata.json'))
                transactions_data = json.loads(zip_file.read('transactions.json'))
                categories_data = json.loads(zip_file.read('categories.json'))
                rules_data = json.loads(zip_file.read('rules.json'))
                accounts_data = json.loads(zip_file.read('accounts.json'))
                import_batches_data = json.loads(zip_file.read('import_batches.json')) if 'import_batches.json' in zip_files else []
                
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in backup file: {str(e)}")
        
        logging.info(f"Flushing current data for user {user_id}")
        await db.transactions.delete_many({"user_id": user_id})
        await db.categories.delete_many({"user_id": user_id})
        await db.category_rules.delete_many({"user_id": user_id})
        await db.accounts.delete_many({"user_id": user_id})
        await db.import_batches.delete_many({"user_id": user_id})
        
        logging.info(f"Restoring data for user {user_id}")
        restored_counts = {"transactions": 0, "categories": 0, "rules": 0, "accounts": 0, "import_batches": 0}
        
        if categories_data:
            for cat in categories_data:
                if cat.get("is_system"):
                    existing = await db.categories.find_one({"id": cat["id"], "is_system": True})
                    if existing:
                        await db.categories.update_one(
                            {"id": cat["id"], "is_system": True},
                            {"$set": {"name": cat["name"], "type": cat["type"]}}
                        )
                    else:
                        await db.categories.insert_one(cat)
                    restored_counts["categories"] += 1
                else:
                    cat["user_id"] = user_id
                    await db.categories.insert_one(cat)
                    restored_counts["categories"] += 1
        
        if transactions_data:
            for txn in transactions_data:
                txn["user_id"] = user_id
            await db.transactions.insert_many(transactions_data)
            restored_counts["transactions"] = len(transactions_data)
        
        if rules_data:
            for rule in rules_data:
                rule["user_id"] = user_id
            await db.category_rules.insert_many(rules_data)
            restored_counts["rules"] = len(rules_data)
        
        if accounts_data:
            for acc in accounts_data:
                acc["user_id"] = user_id
            await db.accounts.insert_many(accounts_data)
            restored_counts["accounts"] = len(accounts_data)
        
        if import_batches_data:
            for batch in import_batches_data:
                batch["user_id"] = user_id
            await db.import_batches.insert_many(import_batches_data)
            restored_counts["import_batches"] = len(import_batches_data)
        
        logging.info(f"Restore completed for user {user_id}: {restored_counts}")
        
        user_info = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "name": 1})
        
        return {
            "success": True,
            "message": "Database restored successfully",
            "pre_restore_backup": str(backup_path),
            "restored_counts": restored_counts,
            "backup_metadata": metadata,
            "restored_to_user": {
                "email": user_info.get("email") if user_info else "unknown",
                "name": user_info.get("name") if user_info else "unknown"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Restore failed for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")
