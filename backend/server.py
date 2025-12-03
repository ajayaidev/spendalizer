from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import pandas as pd
import io
from enum import Enum
import httpx
import json
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7

# Ollama configuration
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3')

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Enums
class AccountType(str, Enum):
    BANK = "BANK"
    CREDIT_CARD = "CREDIT_CARD"

class TransactionDirection(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class CategorisationSource(str, Enum):
    LLM = "LLM"
    RULE = "RULE"
    MANUAL = "MANUAL"
    UNCATEGORISED = "UNCATEGORISED"

class MatchType(str, Enum):
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    REGEX = "REGEX"

class ImportStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"

# Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    password_hash: str = Field(exclude=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Account(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    account_type: AccountType
    institution: str
    last_four: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AccountCreate(BaseModel):
    name: str
    account_type: AccountType
    institution: str
    last_four: Optional[str] = None

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # INCOME, EXPENSE, TRANSFER
    is_system: bool = True
    user_id: Optional[str] = None

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    account_id: str
    import_batch_id: Optional[str] = None
    date: str
    description: str
    amount: float
    direction: TransactionDirection
    transaction_type: AccountType
    category_id: Optional[str] = None
    categorisation_source: CategorisationSource = CategorisationSource.UNCATEGORISED
    confidence_score: Optional[float] = None
    raw_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ImportBatch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    account_id: str
    data_source: str
    original_file_name: str
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_rows: int = 0
    success_count: int = 0
    error_count: int = 0
    duplicate_count: int = 0
    status: ImportStatus = ImportStatus.PENDING
    error_log: Optional[str] = None

class CategoryRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    pattern: str
    match_type: MatchType
    account_id: Optional[str] = None
    category_id: str
    priority: int = 10
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RuleCreate(BaseModel):
    pattern: str
    match_type: MatchType
    account_id: Optional[str] = None
    category_id: str
    priority: int = 10

class CategoryUpdate(BaseModel):
    category_id: str

# Auth Helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    return jwt.encode({"user_id": user_id, "exp": expiration}, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid authentication")

# Initialize default categories
async def init_default_categories():
    default_categories = [
        # Income
        {"name": "Salary", "type": "INCOME", "is_system": True},
        {"name": "Business Income", "type": "INCOME", "is_system": True},
        {"name": "Interest", "type": "INCOME", "is_system": True},
        {"name": "Dividends", "type": "INCOME", "is_system": True},
        {"name": "Refunds/Reimbursements", "type": "INCOME", "is_system": True},
        {"name": "Loan Received", "type": "INCOME", "is_system": True},
        {"name": "Loan Returned Back", "type": "INCOME", "is_system": True},
        {"name": "Other Income", "type": "INCOME", "is_system": True},
        # Expense
        {"name": "Food & Dining", "type": "EXPENSE", "is_system": True},
        {"name": "Groceries", "type": "EXPENSE", "is_system": True},
        {"name": "Utilities", "type": "EXPENSE", "is_system": True},
        {"name": "Transport", "type": "EXPENSE", "is_system": True},
        {"name": "Shopping", "type": "EXPENSE", "is_system": True},
        {"name": "Rent/EMI", "type": "EXPENSE", "is_system": True},
        {"name": "Healthcare", "type": "EXPENSE", "is_system": True},
        {"name": "Education", "type": "EXPENSE", "is_system": True},
        {"name": "Entertainment", "type": "EXPENSE", "is_system": True},
        {"name": "Subscriptions", "type": "EXPENSE", "is_system": True},
        {"name": "Travel", "type": "EXPENSE", "is_system": True},
        {"name": "Miscellaneous", "type": "EXPENSE", "is_system": True},
        {"name": "Loan Given", "type": "EXPENSE", "is_system": True},
        {"name": "Loan Returned Back", "type": "EXPENSE", "is_system": True},
        # Transfer
        {"name": "Bank Transfer", "type": "TRANSFER", "is_system": True},
        {"name": "Credit Card Bill Payment", "type": "TRANSFER", "is_system": True},
        {"name": "Wallet Transfer", "type": "TRANSFER", "is_system": True},
    ]
    
    for cat in default_categories:
        cat_obj = Category(**cat, id=str(uuid.uuid4()))
        existing = await db.categories.find_one({"name": cat["name"], "is_system": True})
        if not existing:
            doc = cat_obj.model_dump()
            doc['created_at'] = doc.get('created_at', datetime.now(timezone.utc)).isoformat()
            await db.categories.insert_one(doc)

# Categorization Engine
async def categorize_with_rules(user_id: str, description: str, account_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    query = {"user_id": user_id, "is_active": True}
    if account_id:
        query["$or"] = [{"account_id": account_id}, {"account_id": None}]
    
    rules = await db.category_rules.find(query).sort("priority", -1).to_list(1000)
    
    description_lower = description.lower()
    
    for rule in rules:
        pattern = rule["pattern"].lower()
        match_type = rule["match_type"]
        
        matched = False
        if match_type == "CONTAINS":
            matched = pattern in description_lower
        elif match_type == "STARTS_WITH":
            matched = description_lower.startswith(pattern)
        elif match_type == "ENDS_WITH":
            matched = description_lower.endswith(pattern)
        elif match_type == "REGEX":
            try:
                matched = re.search(pattern, description_lower) is not None
            except:
                continue
        
        if matched:
            return {
                "category_id": rule["category_id"],
                "categorisation_source": "RULE",
                "confidence_score": 1.0
            }
    
    return None

async def categorize_with_llm(description: str, amount: float, direction: str, transaction_type: str) -> Optional[Dict[str, Any]]:
    try:
        categories = await db.categories.find({"is_system": True}, {"_id": 0}).to_list(1000)
        category_names = [cat["name"] for cat in categories]
        
        prompt = f"""You are an AI trained to classify financial transactions.

Given:
Description: "{description}"
Amount: {amount}
Direction: {direction} (DEBIT or CREDIT)
Account Type: {transaction_type}

Return JSON with:
{{
  "category": "...",
  "confidence": 0.0 - 1.0
}}

Use only these approved categories:
{', '.join(category_names)}

Return only valid JSON, no other text."""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "{}")
                
                try:
                    parsed = json.loads(llm_response)
                    category_name = parsed.get("category")
                    confidence = parsed.get("confidence", 0.5)
                    
                    # Find category by name
                    category = await db.categories.find_one({"name": category_name, "is_system": True})
                    if category:
                        return {
                            "category_id": category["id"],
                            "categorisation_source": "LLM",
                            "confidence_score": confidence
                        }
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        logging.error(f"LLM categorization error: {e}")
    
    return None

async def categorize_transaction(txn: Transaction) -> Dict[str, Any]:
    # First try rules
    rule_result = await categorize_with_rules(txn.user_id, txn.description, txn.account_id)
    if rule_result:
        return rule_result
    
    # Then try LLM
    llm_result = await categorize_with_llm(
        txn.description,
        txn.amount,
        txn.direction.value,
        txn.transaction_type.value
    )
    if llm_result:
        return llm_result
    
    return {
        "category_id": None,
        "categorisation_source": "UNCATEGORISED",
        "confidence_score": None
    }

# Import Engine Helpers
def parse_hdfc_bank_csv(file_content: bytes) -> List[Dict[str, Any]]:
    df = pd.read_csv(io.BytesIO(file_content))
    transactions = []
    
    for _, row in df.iterrows():
        try:
            # Clean raw metadata to avoid NaN values
            raw_dict = row.to_dict()
            clean_metadata = {}
            for k, v in raw_dict.items():
                if pd.notna(v):
                    clean_metadata[k] = v
                else:
                    clean_metadata[k] = None
            
            txn = {
                "date": pd.to_datetime(row["Date"], format="%d/%m/%y").strftime("%Y-%m-%d"),
                "description": str(row["Narration"]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            if pd.notna(row.get("Withdrawal Amt.")):
                txn["amount"] = abs(float(str(row["Withdrawal Amt."]).replace(",", "")))
                txn["direction"] = "DEBIT"
            elif pd.notna(row.get("Deposit Amt.")):
                txn["amount"] = abs(float(str(row["Deposit Amt."]).replace(",", "")))
                txn["direction"] = "CREDIT"
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing row: {e}")
            continue
    
    return transactions

def parse_generic_csv(file_content: bytes, data_source: str) -> List[Dict[str, Any]]:
    # For now, use a generic parser that tries to identify common columns
    df = pd.read_csv(io.BytesIO(file_content))
    transactions = []
    
    # Try to identify date column
    date_col = None
    for col in df.columns:
        if any(word in col.lower() for word in ["date", "txn", "transaction"]):
            date_col = col
            break
    
    # Try to identify description column
    desc_col = None
    for col in df.columns:
        if any(word in col.lower() for word in ["narration", "description", "particulars", "details"]):
            desc_col = col
            break
    
    if not date_col or not desc_col:
        return transactions
    
    for _, row in df.iterrows():
        try:
            txn = {
                "date": pd.to_datetime(row[date_col]).strftime("%Y-%m-%d"),
                "description": str(row[desc_col]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": row.to_dict()
            }
            
            # Try to find amount columns
            for col in df.columns:
                col_lower = col.lower()
                if "withdrawal" in col_lower or "debit" in col_lower:
                    if pd.notna(row[col]):
                        txn["amount"] = abs(float(str(row[col]).replace(",", "").replace("INR", "").strip()))
                        txn["direction"] = "DEBIT"
                elif "deposit" in col_lower or "credit" in col_lower:
                    if pd.notna(row[col]):
                        txn["amount"] = abs(float(str(row[col]).replace(",", "").replace("INR", "").strip()))
                        txn["direction"] = "CREDIT"
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing row: {e}")
            continue
    
    return transactions

async def check_duplicate(user_id: str, account_id: str, date: str, amount: float, description: str) -> bool:
    existing = await db.transactions.find_one({
        "user_id": user_id,
        "account_id": account_id,
        "date": date,
        "amount": amount,
        "description": description
    })
    return existing is not None

# Auth Routes
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password)
    )
    
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc or not verify_password(credentials.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user_doc["id"])
    return {"token": token, "user": {"id": user_doc["id"], "email": user_doc["email"], "name": user_doc["name"]}}

# Account Routes
@api_router.get("/accounts", response_model=List[Account])
async def get_accounts(user_id: str = Depends(get_current_user)):
    accounts = await db.accounts.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    return accounts

@api_router.post("/accounts", response_model=Account)
async def create_account(account_data: AccountCreate, user_id: str = Depends(get_current_user)):
    account = Account(**account_data.model_dump(), user_id=user_id)
    doc = account.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.accounts.insert_one(doc)
    return account

# Category Routes
@api_router.get("/categories", response_model=List[Category])
async def get_categories(user_id: str = Depends(get_current_user)):
    categories = await db.categories.find(
        {"$or": [{"is_system": True}, {"user_id": user_id}]},
        {"_id": 0}
    ).to_list(1000)
    return categories

# Data Sources
@api_router.get("/data-sources")
async def get_data_sources():
    return [
        {"id": "HDFC_BANK", "name": "HDFC Bank", "type": "BANK"},
        {"id": "SBI_BANK", "name": "SBI Bank", "type": "BANK"},
        {"id": "FEDERAL_BANK", "name": "Federal Bank", "type": "BANK"},
        {"id": "HDFC_CC", "name": "HDFC Credit Card", "type": "CREDIT_CARD"},
        {"id": "SBI_CC", "name": "SBI Credit Card", "type": "CREDIT_CARD"},
        {"id": "SCB_CC", "name": "Standard Chartered Credit Card", "type": "CREDIT_CARD"},
    ]

# Import Routes
@api_router.post("/import")
async def import_transactions(
    file: UploadFile = File(...),
    account_id: str = Form(...),
    data_source: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    # Create import batch
    batch = ImportBatch(
        user_id=user_id,
        account_id=account_id,
        data_source=data_source,
        original_file_name=file.filename
    )
    
    try:
        # Read file
        file_content = await file.read()
        
        # Parse based on data source
        if data_source == "HDFC_BANK":
            parsed_txns = parse_hdfc_bank_csv(file_content)
        else:
            parsed_txns = parse_generic_csv(file_content, data_source)
        
        batch.total_rows = len(parsed_txns)
        
        # Get account info
        account = await db.accounts.find_one({"id": account_id, "user_id": user_id})
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Process transactions
        for parsed_txn in parsed_txns:
            # Check duplicate
            is_dup = await check_duplicate(
                user_id,
                account_id,
                parsed_txn["date"],
                parsed_txn["amount"],
                parsed_txn["description"]
            )
            
            if is_dup:
                batch.duplicate_count += 1
                continue
            
            # Create transaction
            txn = Transaction(
                user_id=user_id,
                account_id=account_id,
                import_batch_id=batch.id,
                date=parsed_txn["date"],
                description=parsed_txn["description"],
                amount=parsed_txn["amount"],
                direction=TransactionDirection(parsed_txn["direction"]),
                transaction_type=AccountType(account["account_type"]),
                raw_metadata=parsed_txn.get("raw_metadata")
            )
            
            # Categorize
            cat_result = await categorize_transaction(txn)
            txn.category_id = cat_result.get("category_id")
            txn.categorisation_source = CategorisationSource(cat_result.get("categorisation_source"))
            txn.confidence_score = cat_result.get("confidence_score")
            
            # Save
            doc = txn.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await db.transactions.insert_one(doc)
            batch.success_count += 1
        
        batch.status = ImportStatus.SUCCESS if batch.success_count > 0 else ImportStatus.FAILED
        
        # Save batch
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

# Transaction Routes
@api_router.get("/transactions")
async def get_transactions(
    user_id: str = Depends(get_current_user),
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    query = {"user_id": user_id}
    if account_id:
        query["account_id"] = account_id
    if category_id:
        query["category_id"] = category_id
    if start_date:
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = start_date
    if end_date:
        query["date"] = query.get("date", {})
        query["date"]["$lte"] = end_date
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("date", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.transactions.count_documents(query)
    
    # Fix any invalid values for JSON serialization
    import math
    for txn in transactions:
        # Fix float values
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
        
        # Ensure datetime fields are strings
        if 'created_at' in txn and not isinstance(txn['created_at'], str):
            txn['created_at'] = txn['created_at'].isoformat() if hasattr(txn['created_at'], 'isoformat') else str(txn['created_at'])
        
        if 'updated_at' in txn and not isinstance(txn['updated_at'], str):
            txn['updated_at'] = txn['updated_at'].isoformat() if hasattr(txn['updated_at'], 'isoformat') else str(txn['updated_at'])
        
        # Clean raw_metadata if it exists
        if 'raw_metadata' in txn and txn['raw_metadata']:
            clean_metadata = {}
            for k, v in txn['raw_metadata'].items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    clean_metadata[k] = None
                else:
                    clean_metadata[k] = v
            txn['raw_metadata'] = clean_metadata
    
    return {"transactions": transactions, "total": total}

@api_router.patch("/transactions/{txn_id}/category")
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

# Rules Routes
@api_router.get("/rules", response_model=List[CategoryRule])
async def get_rules(user_id: str = Depends(get_current_user)):
    rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0}).sort("priority", -1).to_list(1000)
    return rules

@api_router.post("/rules", response_model=CategoryRule)
async def create_rule(rule_data: RuleCreate, user_id: str = Depends(get_current_user)):
    rule = CategoryRule(**rule_data.model_dump(), user_id=user_id)
    doc = rule.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.category_rules.insert_one(doc)
    return rule

@api_router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, user_id: str = Depends(get_current_user)):
    result = await db.category_rules.delete_one({"id": rule_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True}

# Analytics Routes
@api_router.get("/analytics/summary")
async def get_analytics_summary(
    user_id: str = Depends(get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    query = {"user_id": user_id}
    if start_date or end_date:
        query["date"] = {}
        if start_date:
            query["date"]["$gte"] = start_date
        if end_date:
            query["date"]["$lte"] = end_date
    
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(10000)
    
    total_income = sum(txn["amount"] for txn in transactions if txn["direction"] == "CREDIT")
    total_expense = sum(txn["amount"] for txn in transactions if txn["direction"] == "DEBIT")
    
    # Category breakdown
    category_breakdown = {}
    for txn in transactions:
        if txn.get("category_id"):
            cat_id = txn["category_id"]
            if cat_id not in category_breakdown:
                category_breakdown[cat_id] = {"total": 0, "count": 0}
            category_breakdown[cat_id]["total"] += txn["amount"]
            category_breakdown[cat_id]["count"] += 1
    
    # Enrich with category names
    enriched_breakdown = []
    for cat_id, data in category_breakdown.items():
        category = await db.categories.find_one({"id": cat_id})
        if category:
            enriched_breakdown.append({
                "category_id": cat_id,
                "category_name": category["name"],
                "category_type": category["type"],
                "total": data["total"],
                "count": data["count"]
            })
    
    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net_savings": round(total_income - total_expense, 2),
        "transaction_count": len(transactions),
        "category_breakdown": sorted(enriched_breakdown, key=lambda x: x["total"], reverse=True)
    }

# Import History
@api_router.get("/imports", response_model=List[ImportBatch])
async def get_import_history(user_id: str = Depends(get_current_user)):
    batches = await db.import_batches.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("imported_at", -1).limit(50).to_list(50)
    return batches

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await init_default_categories()
    logger.info("SpendAlizer API started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
