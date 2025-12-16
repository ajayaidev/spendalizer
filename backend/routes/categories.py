"""Category routes."""
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from database import db
from auth import get_current_user
from models.schemas import Category, CategoryCreate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=List[Category])
async def get_categories(user_id: str = Depends(get_current_user)):
    categories = await db.categories.find(
        {"$or": [{"is_system": True}, {"user_id": user_id}]},
        {"_id": 0}
    ).sort("name", 1).to_list(1000)
    return categories


@router.post("", response_model=Category)
async def create_category(category_data: CategoryCreate, user_id: str = Depends(get_current_user)):
    existing = await db.categories.find_one({
        "name": category_data.name,
        "user_id": user_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    
    category = Category(
        **category_data.model_dump(),
        user_id=user_id,
        is_system=False
    )
    doc = category.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.categories.insert_one(doc)
    return category


@router.put("/{category_id}")
async def update_category(
    category_id: str,
    category_data: CategoryCreate,
    user_id: str = Depends(get_current_user)
):
    result = await db.categories.update_one(
        {"id": category_id, "user_id": user_id, "is_system": False},
        {"$set": category_data.model_dump()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Category not found or is system category")
    return {"success": True}


@router.delete("/{category_id}")
async def delete_category(category_id: str, user_id: str = Depends(get_current_user)):
    txn_count = await db.transactions.count_documents({"category_id": category_id})
    if txn_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category. It is used by {txn_count} transaction(s)"
        )
    
    result = await db.categories.delete_one({
        "id": category_id,
        "user_id": user_id,
        "is_system": False
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found or is system category")
    return {"success": True}
