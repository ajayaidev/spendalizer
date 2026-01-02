"""Transaction routes."""
import math
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form

from database import db
from auth import get_current_user
from models.schemas import (
    Transaction, ImportBatch, CategoryUpdate, BulkCategoryUpdate, BulkRuleCategorize
)
from models.enums import TransactionDirection, AccountType, CategorisationSource, ImportStatus
from services.categorization import categorize_transaction, categorize_with_llm, check_duplicate
from services.parsers import (
    parse_hdfc_bank_excel, parse_hdfc_bank_csv, parse_sbi_csv,
    parse_generic_excel, parse_generic_csv, parse_hdfc_cc_excel
)

router = APIRouter(tags=["transactions"])


@router.get("/data-sources")
async def get_data_sources():
    return [
        {"id": "HDFC_BANK", "name": "HDFC Bank", "type": "BANK"},
        {"id": "SBI_BANK", "name": "SBI Bank", "type": "BANK"},
        {"id": "FEDERAL_BANK", "name": "Federal Bank", "type": "BANK"},
        {"id": "HDFC_CC", "name": "HDFC Credit Card", "type": "CREDIT_CARD"},
        {"id": "SBI_CC", "name": "SBI Credit Card", "type": "CREDIT_CARD"},
        {"id": "SCB_CC", "name": "Standard Chartered Credit Card", "type": "CREDIT_CARD"},
        {"id": "GENERIC_CSV", "name": "Generic CSV/Excel", "type": "BANK"},
    ]


@router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    account_id: str = Form(...),
    data_source: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    batch = ImportBatch(
        user_id=user_id,
        account_id=account_id,
        data_source=data_source,
        original_file_name=file.filename
    )
    
    try:
        file_content = await file.read()
        file_ext = file.filename.lower().split('.')[-1]
        is_excel = file_ext in ['xls', 'xlsx']
        
        logging.info(f"Import: Processing {file.filename} for data_source={data_source}, is_excel={is_excel}")
        
        if data_source == "HDFC_BANK":
            if is_excel:
                parsed_txns = parse_hdfc_bank_excel(file_content)
            else:
                parsed_txns = parse_hdfc_bank_csv(file_content)
        elif data_source == "HDFC_CC":
            # HDFC Credit Card - use dedicated parser
            if is_excel:
                parsed_txns = parse_hdfc_cc_excel(file_content)
            else:
                # For CSV, use generic parser with credit card awareness
                parsed_txns = parse_generic_csv(file_content, data_source)
        elif data_source in ["SBI_BANK", "SBI_CC"]:
            if is_excel:
                parsed_txns = parse_generic_excel(file_content, data_source)
            else:
                parsed_txns = parse_sbi_csv(file_content)
        else:
            # Generic parser for other sources
            if is_excel:
                parsed_txns = parse_generic_excel(file_content, data_source)
            else:
                parsed_txns = parse_generic_csv(file_content, data_source)
        
        batch.total_rows = len(parsed_txns)
        
        account = await db.accounts.find_one({"id": account_id, "user_id": user_id})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        for parsed_txn in parsed_txns:
            is_dup = await check_duplicate(
                user_id, account_id, parsed_txn["date"],
                parsed_txn["amount"], parsed_txn["description"]
            )
            
            if is_dup:
                batch.duplicate_count += 1
                continue
            
            txn = Transaction(
                user_id=user_id,
                account_id=account_id,
                import_batch_id=batch.id,
                date=parsed_txn["date"],
                time=parsed_txn.get("time"),  # Time field for sorting within same day
                description=parsed_txn["description"],
                amount=parsed_txn["amount"],
                direction=TransactionDirection(parsed_txn["direction"]),
                transaction_type=AccountType(account["account_type"]),
                raw_metadata=parsed_txn.get("raw_metadata")
            )
            
            cat_result = await categorize_transaction(
                user_id, txn.description, txn.amount,
                txn.direction.value, txn.transaction_type.value, txn.account_id
            )
            txn.category_id = cat_result.get("category_id")
            txn.categorisation_source = CategorisationSource(cat_result.get("categorisation_source"))
            txn.confidence_score = cat_result.get("confidence_score")
            
            doc = txn.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await db.transactions.insert_one(doc)
            batch.success_count += 1
        
        batch.status = ImportStatus.SUCCESS if batch.success_count > 0 else ImportStatus.FAILED
        
        batch_doc = batch.model_dump()
        batch_doc['imported_at'] = batch_doc['imported_at'].isoformat()
        await db.import_batches.insert_one(batch_doc)
        
        return {
            "batch_id": batch.id,
            "total_rows": batch.total_rows,
            "success_count": batch.success_count,
            "duplicate_count": batch.duplicate_count,
            "error_count": batch.error_count,
            "status": batch.status
        }
    
    except Exception as e:
        logging.error(f"Import error: {e}")
        batch.status = ImportStatus.FAILED
        batch.error_log = str(e)
        batch_doc = batch.model_dump()
        batch_doc['imported_at'] = batch_doc['imported_at'].isoformat()
        await db.import_batches.insert_one(batch_doc)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/transactions")
async def get_transactions(
    user_id: str = Depends(get_current_user),
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    uncategorized: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    query = {"user_id": user_id}
    if account_id:
        query["account_id"] = account_id
    if uncategorized == "true":
        query["$or"] = [{"category_id": None}, {"category_id": ""}]
    elif category_id:
        query["category_id"] = category_id
    if start_date:
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = start_date
    if end_date:
        query["date"] = query.get("date", {})
        query["date"]["$lte"] = end_date
    
    # Sort by date (descending) and then by time (descending) for proper chronological order
    transactions = await db.transactions.find(query, {"_id": 0}).sort([("date", -1), ("time", -1)]).skip(skip).limit(limit).to_list(limit)
    total = await db.transactions.count_documents(query)
    
    for txn in transactions:
        if 'amount' in txn:
            amount = txn['amount']
            if not isinstance(amount, (int, float)) or math.isnan(amount) or math.isinf(amount):
                txn['amount'] = 0.0
            else:
                txn['amount'] = float(amount)
        
        if 'confidence_score' in txn and txn['confidence_score'] is not None:
            score = txn['confidence_score']
            if not isinstance(score, (int, float)) or math.isnan(score) or math.isinf(score):
                txn['confidence_score'] = None
            else:
                txn['confidence_score'] = float(score)
        
        if 'created_at' in txn and not isinstance(txn['created_at'], str):
            txn['created_at'] = txn['created_at'].isoformat() if hasattr(txn['created_at'], 'isoformat') else str(txn['created_at'])
        
        if 'updated_at' in txn and not isinstance(txn['updated_at'], str):
            txn['updated_at'] = txn['updated_at'].isoformat() if hasattr(txn['updated_at'], 'isoformat') else str(txn['updated_at'])
        
        if 'raw_metadata' in txn and txn['raw_metadata']:
            clean_metadata = {}
            for k, v in txn['raw_metadata'].items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    clean_metadata[k] = None
                else:
                    clean_metadata[k] = v
            txn['raw_metadata'] = clean_metadata
    
    return {"transactions": transactions, "total": total}


@router.patch("/transactions/{txn_id}/category")
async def update_transaction_category(
    txn_id: str,
    update: CategoryUpdate,
    user_id: str = Depends(get_current_user)
):
    result = await db.transactions.update_one(
        {"id": txn_id, "user_id": user_id},
        {
            "$set": {
                "category_id": update.category_id,
                "categorisation_source": "MANUAL",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {"success": True}


@router.post("/transactions/bulk-categorize")
async def bulk_categorize_transactions(
    update: BulkCategoryUpdate,
    user_id: str = Depends(get_current_user)
):
    result = await db.transactions.update_many(
        {"id": {"$in": update.transaction_ids}, "user_id": user_id},
        {
            "$set": {
                "category_id": update.category_id,
                "categorisation_source": "MANUAL",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "updated_count": result.modified_count
    }


@router.post("/transactions/bulk-categorize-by-rules")
async def bulk_categorize_by_rules(
    update: BulkRuleCategorize,
    user_id: str = Depends(get_current_user)
):
    rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0}).sort("priority", -1).to_list(1000)
    
    if not rules:
        return {
            "success": True,
            "updated_count": 0,
            "message": "No rules found. Please create categorization rules first."
        }
    
    updated_count = 0
    for txn_id in update.transaction_ids:
        txn = await db.transactions.find_one({"id": txn_id, "user_id": user_id})
        if not txn:
            continue
            
        description = txn.get("description", "").strip().lower()
        
        for rule in rules:
            pattern = rule["pattern"].strip().lower()
            match_type = rule["match_type"]
            
            matched = False
            if match_type == "CONTAINS" and pattern in description:
                matched = True
            elif match_type == "STARTS_WITH" and description.startswith(pattern):
                matched = True
            elif match_type == "ENDS_WITH" and description.endswith(pattern):
                matched = True
            elif match_type == "EXACT" and description == pattern:
                matched = True
            
            if matched:
                await db.transactions.update_one(
                    {"id": txn_id},
                    {
                        "$set": {
                            "category_id": rule["category_id"],
                            "categorisation_source": "RULE",
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                updated_count += 1
                break
    
    return {
        "success": True,
        "updated_count": updated_count,
        "total_processed": len(update.transaction_ids),
        "rules_available": len(rules)
    }


@router.post("/transactions/bulk-categorize-by-ai")
async def bulk_categorize_by_ai(
    update: BulkRuleCategorize,
    user_id: str = Depends(get_current_user)
):
    categories = await db.categories.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    
    if not categories:
        raise HTTPException(status_code=400, detail="No categories found.")
    
    updated_count = 0
    for txn_id in update.transaction_ids:
        txn = await db.transactions.find_one({"id": txn_id, "user_id": user_id})
        if not txn:
            continue
        
        account = await db.accounts.find_one({"id": txn.get("account_id")})
        transaction_type = account.get("type", "SAVINGS") if account else "SAVINGS"
        
        result = await categorize_with_llm(
            txn.get("description", ""),
            txn.get("amount", 0.0),
            txn.get("direction", "DEBIT"),
            transaction_type,
            user_id
        )
        
        if result and result.get("category_id"):
            await db.transactions.update_one(
                {"id": txn_id},
                {
                    "$set": {
                        "category_id": result["category_id"],
                        "categorisation_source": "AI",
                        "confidence_score": result.get("confidence_score", 0.0),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            updated_count += 1
    
    return {
        "success": True,
        "updated_count": updated_count
    }


@router.get("/import-history")
async def get_import_history(user_id: str = Depends(get_current_user)):
    batches = await db.import_batches.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("imported_at", -1).limit(50).to_list(50)
    return batches


# Alias for frontend compatibility
@router.get("/imports")
async def get_imports(user_id: str = Depends(get_current_user)):
    """Alias endpoint for /import-history (frontend uses this route)."""
    batches = await db.import_batches.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("imported_at", -1).limit(50).to_list(50)
    return batches
