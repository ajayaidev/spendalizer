"""Rules routes."""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from database import db
from auth import get_current_user
from models.schemas import CategoryRule, RuleCreate

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleImport(BaseModel):
    rules: List[Dict[str, Any]]


@router.get("")
async def get_rules(user_id: str = Depends(get_current_user)):
    rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0}).sort("priority", -1).to_list(1000)
    return rules


@router.post("", response_model=CategoryRule)
async def create_rule(rule_data: RuleCreate, user_id: str = Depends(get_current_user)):
    rule = CategoryRule(**rule_data.model_dump(), user_id=user_id)
    doc = rule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.category_rules.insert_one(doc)
    return rule


@router.put("/{rule_id}")
async def update_rule(rule_id: str, rule_data: RuleCreate, user_id: str = Depends(get_current_user)):
    existing_rule = await db.category_rules.find_one({"id": rule_id, "user_id": user_id})
    if not existing_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    category = await db.categories.find_one({
        "id": rule_data.category_id,
        "$or": [{"is_system": True}, {"user_id": user_id}]
    })
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")
    
    update_data = {
        "pattern": rule_data.pattern,
        "match_type": rule_data.match_type,
        "category_id": rule_data.category_id,
        "priority": rule_data.priority,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.category_rules.update_one(
        {"id": rule_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0 and result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"success": True, "message": "Rule updated successfully"}


@router.delete("/{rule_id}")
async def delete_rule(rule_id: str, user_id: str = Depends(get_current_user)):
    result = await db.category_rules.delete_one({"id": rule_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True}


@router.get("/export")
async def export_rules(user_id: str = Depends(get_current_user)):
    rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0, "user_id": 0}).to_list(1000)
    
    for rule in rules:
        category = await db.categories.find_one({"id": rule.get("category_id")})
        if category:
            rule["category_name"] = category.get("name")
    
    return rules


@router.post("/import")
async def import_rules(data: RuleImport, user_id: str = Depends(get_current_user)):
    imported_count = 0
    skipped_count = 0
    
    for rule_data in data.rules:
        rule_data.pop("id", None)
        rule_data.pop("category_name", None)
        
        if "category_id" in rule_data:
            category = await db.categories.find_one({
                "$and": [
                    {"id": rule_data["category_id"]},
                    {"$or": [{"is_system": True}, {"user_id": user_id}]}
                ]
            })
            if not category:
                skipped_count += 1
                continue
        
        rule_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "pattern": rule_data.get("pattern", ""),
            "match_type": rule_data.get("match_type", "CONTAINS"),
            "account_id": rule_data.get("account_id"),
            "category_id": rule_data.get("category_id"),
            "priority": rule_data.get("priority", 10),
            "is_active": rule_data.get("is_active", True),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.category_rules.insert_one(rule_doc)
        imported_count += 1
    
    return {
        "success": True,
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "message": f"Imported {imported_count} rules, skipped {skipped_count} (missing categories)"
    }
