"""Account routes."""
from typing import List
from fastapi import APIRouter, Depends

from database import db
from auth import get_current_user
from models.schemas import Account, AccountCreate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=List[Account])
async def get_accounts(user_id: str = Depends(get_current_user)):
    accounts = await db.accounts.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    return accounts


@router.post("", response_model=Account)
async def create_account(account_data: AccountCreate, user_id: str = Depends(get_current_user)):
    account = Account(**account_data.model_dump(), user_id=user_id)
    doc = account.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.accounts.insert_one(doc)
    return account
