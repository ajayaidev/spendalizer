from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends, status, Request
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
import secrets
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# Email configuration
SMTP_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('EMAIL_PORT', '587'))
SMTP_USER = os.environ.get('EMAIL_USER', '')
SMTP_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
FROM_EMAIL = os.environ.get('EMAIL_FROM', SMTP_USER)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

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
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class DeleteAllTransactionsRequest(BaseModel):
    confirmation_text: str

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
    parent_category_id: Optional[str] = None  # For sub-categories
    is_system: bool = True
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CategoryCreate(BaseModel):
    name: str
    type: str
    parent_category_id: Optional[str] = None

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

# Email helper
async def send_email(to_email: str, subject: str, body: str):
    """Send email using SMTP"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logging.warning("Email not configured. Skipping email send.")
        return False
    
    try:
        logging.info(f"Attempting to send email using {SMTP_HOST}:{SMTP_PORT} with user {SMTP_USER}")
        message = MIMEMultipart()
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
        )
        logging.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

def generate_reset_token() -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(32)

# Initialize default categories from fixed JSON file
# This ensures system categories have consistent IDs across all environments
async def init_default_categories():
    # Load system categories from JSON file (version controlled)
    system_categories_path = ROOT_DIR / 'system_categories.json'
    
    try:
        with open(system_categories_path, 'r') as f:
            default_categories = json.load(f)
    except FileNotFoundError:
        logging.error(f"System categories file not found: {system_categories_path}")
        return
    
    for cat_data in default_categories:
        # Use the predefined ID from the JSON file
        existing = await db.categories.find_one({"id": cat_data["id"]})
        if not existing:
            # Insert with predefined ID
            cat_data['created_at'] = datetime.now(timezone.utc).isoformat()
            await db.categories.insert_one(cat_data)
            logging.info(f"Initialized system category: {cat_data['name']} (id: {cat_data['id']})")
        else:
            # Category already exists - update name and type if changed
            updates = {}
            if existing.get("name") != cat_data["name"]:
                updates["name"] = cat_data["name"]
            if existing.get("type") != cat_data["type"]:
                updates["type"] = cat_data["type"]
            
            if updates:
                await db.categories.update_one(
                    {"id": cat_data["id"]},
                    {"$set": updates}
                )
                logging.info(f"Updated system category: {cat_data['name']} - {updates}")
            else:
                logging.debug(f"System category already up-to-date: {cat_data['name']}")

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

async def categorize_with_llm(description: str, amount: float, direction: str, transaction_type: str, user_id: str) -> Optional[Dict[str, Any]]:
    try:
        # Get both system categories AND user's custom categories
        categories = await db.categories.find(
            {"$or": [{"is_system": True}, {"user_id": user_id}]},
            {"_id": 0}
        ).to_list(1000)
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
                    
                    # Find category by name (system or user category)
                    category = await db.categories.find_one({
                        "name": category_name,
                        "$or": [{"is_system": True}, {"user_id": user_id}]
                    })
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
        txn.transaction_type.value,
        txn.user_id  # Pass user_id for user categories
    )
    if llm_result:
        return llm_result
    
    return {
        "category_id": None,
        "categorisation_source": "UNCATEGORISED",
        "confidence_score": None
    }

# Import Engine Helpers
def parse_hdfc_bank_excel(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse HDFC Bank Excel file"""
    try:
        # HDFC Bank Excel files often have headers at row 20 (0-indexed)
        # Try reading with skiprows to find the correct header
        df = None
        for skip in [20, 0, 10, 15]:  # Try common header positions
            try:
                temp_df = pd.read_excel(io.BytesIO(file_content), skiprows=skip)
                # Check if this looks like transaction data
                if any(col for col in temp_df.columns if 'date' in str(col).lower()):
                    df = temp_df
                    logging.info(f"Found headers at row {skip}, loaded {len(df)} rows")
                    break
            except:
                continue
        
        if df is None:
            # Fallback to reading without skipping
            df = pd.read_excel(io.BytesIO(file_content))
            logging.info(f"Successfully parsed Excel file with {len(df)} rows")
    except Exception as e:
        logging.error(f"Failed to parse Excel file: {e}")
        raise ValueError(f"Could not parse Excel file: {str(e)}")
    
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
            
            # Find the date column (case-insensitive)
            date_col = None
            for col in df.columns:
                if 'date' in str(col).lower():
                    date_col = col
                    break
            
            # Find the narration/description column
            narration_col = None
            for col in df.columns:
                if any(word in str(col).lower() for word in ['narration', 'description', 'particulars']):
                    narration_col = col
                    break
            
            if not date_col or not narration_col:
                logging.debug(f"Skipping row - missing required columns")
                continue
            
            # Parse date - try multiple formats
            date_str = str(row[date_col]).strip()
            try:
                # Try common date formats
                txn_date = pd.to_datetime(date_str, dayfirst=True).strftime("%Y-%m-%d")
            except:
                logging.warning(f"Could not parse date: {date_str}")
                continue
            
            txn = {
                "date": txn_date,
                "description": str(row[narration_col]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            # Find withdrawal/deposit columns (case-insensitive)
            withdrawal_col = None
            deposit_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if 'withdrawal' in col_lower or 'debit' in col_lower:
                    withdrawal_col = col
                elif 'deposit' in col_lower or 'credit' in col_lower:
                    deposit_col = col
            
            # Parse amounts
            if withdrawal_col and pd.notna(row.get(withdrawal_col)):
                amount_str = str(row[withdrawal_col]).replace(",", "").replace("INR", "").strip()
                try:
                    txn["amount"] = abs(float(amount_str))
                    txn["direction"] = "DEBIT"
                except ValueError:
                    pass
            
            if deposit_col and pd.notna(row.get(deposit_col)):
                amount_str = str(row[deposit_col]).replace(",", "").replace("INR", "").strip()
                try:
                    txn["amount"] = abs(float(amount_str))
                    txn["direction"] = "CREDIT"
                except ValueError:
                    pass
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing Excel row: {e}")
            continue
    
    return transactions

def parse_generic_excel(file_content: bytes, data_source: str) -> List[Dict[str, Any]]:
    """Parse generic Excel file - handles .xlsx, .xls, and HTML-based Excel files"""
    df = None
    
    try:
        # Check if it's actually an HTML file disguised as Excel (common with some banks)
        file_str = file_content[:1000].decode('utf-8', errors='ignore').lower()
        if '<html' in file_str or '<table' in file_str or '<!doctype' in file_str:
            logging.info("Detected HTML-based Excel file, using HTML parser")
            df = pd.read_html(io.BytesIO(file_content))[0]  # Get first table
            logging.info(f"Successfully parsed HTML table with {len(df)} rows")
        else:
            # Try openpyxl engine first (for .xlsx files)
            try:
                df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
                logging.info(f"Successfully parsed Excel file with openpyxl engine: {len(df)} rows")
            except Exception as e1:
                logging.debug(f"openpyxl failed: {e1}")
                # Fall back to xlrd for older .xls files
                try:
                    df = pd.read_excel(io.BytesIO(file_content), engine='xlrd')
                    logging.info(f"Successfully parsed Excel file with xlrd engine: {len(df)} rows")
                except Exception as e2:
                    logging.debug(f"xlrd failed: {e2}")
                    # Last resort: try HTML parser
                    df = pd.read_html(io.BytesIO(file_content))[0]
                    logging.info(f"Successfully parsed as HTML table with {len(df)} rows")
    except Exception as e:
        logging.error(f"Failed to parse Excel file: {e}")
        raise ValueError(f"Could not parse Excel file. Please ensure it's a valid Excel file (.xlsx or .xls) or try exporting as CSV instead.")
    
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
        logging.warning(f"Could not identify required columns. Columns found: {df.columns.tolist()}")
        return transactions
    
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
                "date": pd.to_datetime(row[date_col]).strftime("%Y-%m-%d"),
                "description": str(row[desc_col]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            # Try to find amount columns
            for col in df.columns:
                col_lower = col.lower()
                if "withdrawal" in col_lower or "debit" in col_lower:
                    if pd.notna(row[col]):
                        amount_str = str(row[col]).replace(",", "").replace("INR", "").strip()
                        txn["amount"] = abs(float(amount_str))
                        txn["direction"] = "DEBIT"
                elif "deposit" in col_lower or "credit" in col_lower:
                    if pd.notna(row[col]):
                        amount_str = str(row[col]).replace(",", "").replace("INR", "").strip()
                        txn["amount"] = abs(float(amount_str))
                        txn["direction"] = "CREDIT"
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing Excel row: {e}")
            continue
    
    return transactions

def parse_hdfc_bank_csv(file_content: bytes) -> List[Dict[str, Any]]:
    # Try different encodings to handle various file formats
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
            logging.info(f"Successfully decoded CSV with {encoding} encoding")
            break
        except (UnicodeDecodeError, Exception) as e:
            logging.debug(f"Failed to decode with {encoding}: {e}")
            continue
    
    if df is None:
        raise ValueError("Could not decode file. Please ensure it's a valid CSV file.")
    
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
            
            # Find withdrawal/deposit columns (case-insensitive)
            withdrawal_col = None
            deposit_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if 'withdrawal' in col_lower or 'debit' in col_lower:
                    withdrawal_col = col
                elif 'deposit' in col_lower or 'credit' in col_lower:
                    deposit_col = col
            
            # Parse amounts
            if withdrawal_col and pd.notna(row.get(withdrawal_col)):
                amount_str = str(row[withdrawal_col]).replace(",", "").replace("INR", "").strip()
                try:
                    txn["amount"] = abs(float(amount_str))
                    txn["direction"] = "DEBIT"
                except ValueError:
                    pass
            
            if deposit_col and pd.notna(row.get(deposit_col)):
                amount_str = str(row[deposit_col]).replace(",", "").replace("INR", "").strip()
                try:
                    txn["amount"] = abs(float(amount_str))
                    txn["direction"] = "CREDIT"
                except ValueError:
                    pass
            
            if txn["amount"] > 0:
                transactions.append(txn)
        except Exception as e:
            logging.error(f"Error parsing row: {e}")
            continue
    
    return transactions

def parse_sbi_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse SBI Bank CSV format with multiple header rows"""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    
    for encoding in encodings:
        try:
            # Read the entire file as text first
            text_content = file_content.decode(encoding)
            lines = text_content.split('\n')
            
            # Find the header row (contains "Txn Date")
            header_line_idx = None
            for idx, line in enumerate(lines):
                if 'Txn Date' in line or 'txn date' in line.lower():
                    header_line_idx = idx
                    break
            
            if header_line_idx is None:
                logging.warning("Could not find header row with 'Txn Date'")
                continue
            
            # Create a CSV from header line onwards
            csv_content = '\n'.join(lines[header_line_idx:])
            df = pd.read_csv(io.StringIO(csv_content))
            logging.info(f"Successfully parsed SBI CSV with {len(df)} rows using {encoding} encoding")
            
            transactions = []
            
            for _, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('Txn Date')) or pd.isna(row.get('Description')):
                        continue
                    
                    # Clean raw metadata
                    raw_dict = row.to_dict()
                    clean_metadata = {}
                    for k, v in raw_dict.items():
                        if pd.notna(v):
                            clean_metadata[k] = v
                        else:
                            clean_metadata[k] = None
                    
                    # Parse date (format: DD-MMM-YY)
                    date_str = str(row['Txn Date']).strip()
                    date_obj = pd.to_datetime(date_str, format='%d-%b-%y')
                    
                    # Get description
                    description = str(row['Description']).strip()
                    
                    # Determine amount and direction
                    debit_col = [col for col in df.columns if 'debit' in col.lower()][0]
                    credit_col = [col for col in df.columns if 'credit' in col.lower()][0]
                    
                    amount = 0.0
                    direction = "DEBIT"
                    
                    if pd.notna(row[debit_col]):
                        amount_str = str(row[debit_col]).replace(",", "").replace("INR", "").strip()
                        if amount_str:
                            amount = abs(float(amount_str))
                            direction = "DEBIT"
                    elif pd.notna(row[credit_col]):
                        amount_str = str(row[credit_col]).replace(",", "").replace("INR", "").strip()
                        if amount_str:
                            amount = abs(float(amount_str))
                            direction = "CREDIT"
                    
                    if amount > 0:
                        txn = {
                            "date": date_obj.strftime("%Y-%m-%d"),
                            "description": description,
                            "amount": amount,
                            "direction": direction,
                            "raw_metadata": clean_metadata
                        }
                        transactions.append(txn)
                
                except Exception as e:
                    logging.error(f"Error parsing SBI row: {e}")
                    continue
            
            return transactions
            
        except Exception as e:
            logging.debug(f"Failed to parse SBI CSV with {encoding}: {e}")
            continue
    
    raise ValueError("Could not parse SBI CSV file. Please ensure it's a valid SBI statement export.")

def parse_generic_csv(file_content: bytes, data_source: str) -> List[Dict[str, Any]]:
    # Try different encodings to handle various file formats
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
            logging.info(f"Successfully decoded CSV with {encoding} encoding")
            break
        except (UnicodeDecodeError, Exception) as e:
            logging.debug(f"Failed to decode with {encoding}: {e}")
            continue
    
    if df is None:
        raise ValueError("Could not decode file. Please ensure it's a valid CSV file.")
    
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
            # Clean raw metadata to avoid NaN values
            raw_dict = row.to_dict()
            clean_metadata = {}
            for k, v in raw_dict.items():
                if pd.notna(v):
                    clean_metadata[k] = v
                else:
                    clean_metadata[k] = None
            
            txn = {
                "date": pd.to_datetime(row[date_col]).strftime("%Y-%m-%d"),
                "description": str(row[desc_col]).strip(),
                "amount": 0.0,
                "direction": "DEBIT",
                "raw_metadata": clean_metadata
            }
            
            # Try to find amount columns
            for col in df.columns:
                col_lower = col.lower()
                if "withdrawal" in col_lower or "debit" in col_lower:
                    if pd.notna(row[col]):
                        amount_str = str(row[col]).replace(",", "").replace("INR", "").strip()
                        txn["amount"] = abs(float(amount_str))
                        txn["direction"] = "DEBIT"
                elif "deposit" in col_lower or "credit" in col_lower:
                    if pd.notna(row[col]):
                        amount_str = str(row[col]).replace(",", "").replace("INR", "").strip()
                        txn["amount"] = abs(float(amount_str))
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
    
    # Create document manually to ensure password_hash is included
    doc = {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'password_hash': user.password_hash,
        'created_at': user.created_at.isoformat()
    }
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

@api_router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, req: Request):
    # Find user by email
    user_doc = await db.users.find_one({"email": request.email})
    
    # Always return success to prevent email enumeration
    if not user_doc:
        logging.info(f"Password reset requested for non-existent email: {request.email}")
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_reset_token()
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Store reset token in database
    await db.users.update_one(
        {"id": user_doc["id"]},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expiration": expiration.isoformat()
        }}
    )
    
    # Determine frontend URL from request origin or fallback to env variable
    origin = req.headers.get("origin") or req.headers.get("referer", "").rstrip("/")
    if origin and origin.startswith("http"):
        frontend_url = origin
    else:
        frontend_url = FRONTEND_URL
    
    # Send email
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    email_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Reset Your SpendAlizer Password</h2>
            <p>Hi {user_doc['name']},</p>
            <p>You requested to reset your password. Click the button below to reset it:</p>
            <p style="margin: 30px 0;">
                <a href="{reset_link}" 
                   style="background-color: #4169E1; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="color: #666; word-break: break-all;">{reset_link}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #999; font-size: 12px;">SpendAlizer - Personal Finance Management</p>
        </body>
    </html>
    """
    
    await send_email(request.email, "Reset Your Password - SpendAlizer", email_body)
    
    return {"message": "If the email exists, a reset link has been sent"}

@api_router.post("/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    # Find user with valid reset token
    user_doc = await db.users.find_one({"reset_token": request.token})
    
    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Check if token is expired
    expiration = datetime.fromisoformat(user_doc.get("reset_token_expiration", ""))
    if datetime.now(timezone.utc) > expiration:
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Update password and clear reset token
    new_password_hash = hash_password(request.new_password)
    await db.users.update_one(
        {"id": user_doc["id"]},
        {"$set": {
            "password_hash": new_password_hash
        },
        "$unset": {
            "reset_token": "",
            "reset_token_expiration": ""
        }}
    )
    
    return {"message": "Password reset successful"}

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
    ).sort("name", 1).to_list(1000)  # Sort alphabetically by name
    return categories

@api_router.post("/categories", response_model=Category)
async def create_category(category_data: CategoryCreate, user_id: str = Depends(get_current_user)):
    # Check if category name already exists for this user
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

@api_router.put("/categories/{category_id}")
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

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user_id: str = Depends(get_current_user)):
    # Check if category is being used
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
        
        # Detect file type from extension
        file_ext = file.filename.lower().split('.')[-1]
        is_excel = file_ext in ['xls', 'xlsx']
        
        # Parse based on data source and file type
        if data_source == "HDFC_BANK":
            if is_excel:
                parsed_txns = parse_hdfc_bank_excel(file_content)
            else:
                parsed_txns = parse_hdfc_bank_csv(file_content)
        elif data_source in ["SBI_BANK", "SBI_CC"]:
            if is_excel:
                parsed_txns = parse_generic_excel(file_content, data_source)
            else:
                parsed_txns = parse_sbi_csv(file_content)
        else:
            if is_excel:
                parsed_txns = parse_generic_excel(file_content, data_source)
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

# Bulk update transactions
class BulkCategoryUpdate(BaseModel):
    transaction_ids: List[str]
    category_id: str

@api_router.post("/transactions/bulk-categorize")
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

# Bulk categorize using rules
class BulkRuleCategorize(BaseModel):
    transaction_ids: List[str]

@api_router.post("/transactions/bulk-categorize-by-rules")
async def bulk_categorize_by_rules(
    update: BulkRuleCategorize,
    user_id: str = Depends(get_current_user)
):
    # Get all rules for this user sorted by priority
    rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0}).sort("priority", -1).to_list(1000)
    
    if not rules:
        logging.info(f"No rules found for user {user_id}")
        return {
            "success": True,
            "updated_count": 0,
            "message": "No rules found. Please create categorization rules first."
        }
    
    logging.info(f"Found {len(rules)} rules for user {user_id}")
    
    updated_count = 0
    matched_count = 0
    for txn_id in update.transaction_ids:
        txn = await db.transactions.find_one({"id": txn_id, "user_id": user_id})
        if not txn:
            logging.warning(f"Transaction {txn_id} not found")
            continue
            
        description = txn.get("description", "").strip().lower()
        logging.info(f"Processing transaction: '{description}'")
        
        # Match against rules
        for rule in rules:
            pattern = rule["pattern"].strip().lower()
            match_type = rule["match_type"]
            
            logging.debug(f"Checking rule - Pattern: '{pattern}', Type: {match_type}")
            
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
                logging.info(f"✓ Matched! Pattern: '{pattern}' ({match_type}) -> Category: {rule['category_id']}")
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
                matched_count += 1
                break  # Stop after first match (highest priority)
    
    logging.info(f"Bulk categorization by rules complete: {updated_count} transactions updated out of {len(update.transaction_ids)}")
    
    return {
        "success": True,
        "updated_count": updated_count,
        "total_processed": len(update.transaction_ids),
        "rules_available": len(rules)
    }

# Bulk categorize using AI/LLM
@api_router.post("/transactions/bulk-categorize-by-ai")
async def bulk_categorize_by_ai(
    update: BulkRuleCategorize,
    user_id: str = Depends(get_current_user)
):
    # Get all categories
    categories = await db.categories.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    
    if not categories:
        raise HTTPException(status_code=400, detail="No categories found. Please create categories first.")
    
    updated_count = 0
    for txn_id in update.transaction_ids:
        txn = await db.transactions.find_one({"id": txn_id, "user_id": user_id})
        if not txn:
            continue
        
        # Get account info for transaction type
        account = await db.accounts.find_one({"id": txn.get("account_id")})
        transaction_type = account.get("type", "SAVINGS") if account else "SAVINGS"
        
        # Use existing categorize_with_llm function with all required parameters
        result = await categorize_with_llm(
            txn.get("description", ""),
            txn.get("amount", 0.0),
            txn.get("direction", "DEBIT"),
            transaction_type,
            user_id  # Pass user_id for user categories
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

@api_router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, rule_data: RuleCreate, user_id: str = Depends(get_current_user)):
    # Verify rule exists and belongs to user
    existing_rule = await db.category_rules.find_one({"id": rule_id, "user_id": user_id})
    if not existing_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Verify category exists
    category = await db.categories.find_one({
        "id": rule_data.category_id,
        "$or": [{"is_system": True}, {"user_id": user_id}]
    })
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")
    
    # Update rule
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

@api_router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, user_id: str = Depends(get_current_user)):
    result = await db.category_rules.delete_one({"id": rule_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True}

@api_router.get("/rules/export")
async def export_rules(user_id: str = Depends(get_current_user)):
    rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0, "user_id": 0}).to_list(1000)
    
    # Get category names for better readability
    for rule in rules:
        category = await db.categories.find_one({"id": rule.get("category_id")})
        if category:
            rule["category_name"] = category.get("name")
    
    return rules

class RuleImport(BaseModel):
    rules: List[Dict[str, Any]]

@api_router.post("/rules/import")
async def import_rules(data: RuleImport, user_id: str = Depends(get_current_user)):
    imported_count = 0
    skipped_count = 0
    
    for rule_data in data.rules:
        # Remove id and category_name if present
        rule_data.pop("id", None)
        rule_data.pop("category_name", None)
        
        # Check if category_id exists for this user (including system categories)
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
        
        # Create new rule
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
    uncategorized_total = 0
    uncategorized_count = 0
    
    for txn in transactions:
        if txn.get("category_id"):
            cat_id = txn["category_id"]
            if cat_id not in category_breakdown:
                category_breakdown[cat_id] = {"total": 0, "count": 0}
            category_breakdown[cat_id]["total"] += txn["amount"]
            category_breakdown[cat_id]["count"] += 1
        else:
            # Count uncategorized transactions
            uncategorized_total += txn["amount"]
            uncategorized_count += 1
    
    # Enrich with category names and split transfers by direction
    enriched_breakdown = []
    for cat_id, data in category_breakdown.items():
        # Find category - check both system categories and user categories
        category = await db.categories.find_one({
            "id": cat_id,
            "$or": [{"is_system": True}, {"user_id": user_id}]
        })
        if category:
            cat_type = category["type"]
            
            # Handle new explicit IN/OUT types
            if cat_type in ["TRANSFER_INTERNAL_IN", "TRANSFER_EXTERNAL_IN"]:
                # Explicit IN categories - only show in IN
                incoming_total = sum(txn["amount"] for txn in transactions 
                                   if txn.get("category_id") == cat_id)
                incoming_count = len([txn for txn in transactions 
                                    if txn.get("category_id") == cat_id])
                
                if incoming_count > 0:
                    enriched_breakdown.append({
                        "category_id": cat_id,
                        "category_name": category["name"],
                        "category_type": cat_type.replace("TRANSFER_", "TRANSFER_").replace("_IN", "_IN"),
                        "total": incoming_total,
                        "count": incoming_count
                    })
            elif cat_type in ["TRANSFER_INTERNAL_OUT", "TRANSFER_EXTERNAL_OUT"]:
                # Explicit OUT categories - only show in OUT
                outgoing_total = sum(txn["amount"] for txn in transactions 
                                   if txn.get("category_id") == cat_id)
                outgoing_count = len([txn for txn in transactions 
                                    if txn.get("category_id") == cat_id])
                
                if outgoing_count > 0:
                    enriched_breakdown.append({
                        "category_id": cat_id,
                        "category_name": category["name"],
                        "category_type": cat_type.replace("TRANSFER_", "TRANSFER_").replace("_OUT", "_OUT"),
                        "total": outgoing_total,
                        "count": outgoing_count
                    })
            # Handle legacy transfer types (split by direction)
            elif cat_type in ["TRANSFER", "TRANSFER_INTERNAL", "TRANSFER_EXTERNAL"]:
                # Get incoming (CREDIT) transfers
                incoming_total = sum(txn["amount"] for txn in transactions 
                                   if txn.get("category_id") == cat_id and txn["direction"] == "CREDIT")
                incoming_count = sum(1 for txn in transactions 
                                   if txn.get("category_id") == cat_id and txn["direction"] == "CREDIT")
                
                # Get outgoing (DEBIT) transfers
                outgoing_total = sum(txn["amount"] for txn in transactions 
                                   if txn.get("category_id") == cat_id and txn["direction"] == "DEBIT")
                outgoing_count = sum(1 for txn in transactions 
                                   if txn.get("category_id") == cat_id and txn["direction"] == "DEBIT")
                
                # Determine the final type for display
                if cat_type == "TRANSFER_INTERNAL":
                    display_type_in = "TRANSFER_INTERNAL_IN"
                    display_type_out = "TRANSFER_INTERNAL_OUT"
                elif cat_type == "TRANSFER_EXTERNAL":
                    display_type_in = "TRANSFER_EXTERNAL_IN"
                    display_type_out = "TRANSFER_EXTERNAL_OUT"
                else:  # Legacy TRANSFER
                    display_type_in = "TRANSFER_IN"
                    display_type_out = "TRANSFER_OUT"
                
                if incoming_count > 0:
                    enriched_breakdown.append({
                        "category_id": cat_id,
                        "category_name": category["name"],
                        "category_type": display_type_in,
                        "total": incoming_total,
                        "count": incoming_count
                    })
                
                if outgoing_count > 0:
                    enriched_breakdown.append({
                        "category_id": cat_id,
                        "category_name": category["name"],
                        "category_type": display_type_out,
                        "total": outgoing_total,
                        "count": outgoing_count
                    })
            else:
                enriched_breakdown.append({
                    "category_id": cat_id,
                    "category_name": category["name"],
                    "category_type": category["type"],
                    "total": data["total"],
                    "count": data["count"]
                })
    
    # Add uncategorized if any
    if uncategorized_count > 0:
        enriched_breakdown.append({
            "category_id": None,
            "category_name": "Uncategorized",
            "category_type": "UNCATEGORIZED",
            "total": uncategorized_total,
            "count": uncategorized_count
        })
    
    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net_savings": round(total_income - total_expense, 2),
        "transaction_count": len(transactions),
        "category_breakdown": sorted(enriched_breakdown, key=lambda x: x["total"], reverse=True)
    }

@api_router.get("/analytics/spending-over-time")
async def get_spending_over_time(
    user_id: str = Depends(get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "month"  # month, week, day
):
    query = {"user_id": user_id}
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        query.setdefault("date", {})["$lte"] = end_date
    
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(10000)
    
    # Group transactions by date period
    from collections import defaultdict
    grouped_data = defaultdict(lambda: {
        "income": 0, 
        "expense": 0, 
        "transfer_internal_in": 0, 
        "transfer_internal_out": 0,
        "transfer_external_in": 0,
        "transfer_external_out": 0
    })
    
    for txn in transactions:
        date_str = txn.get("date", "")
        if not date_str:
            continue
            
        # Format date based on grouping
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if group_by == "month":
                period_key = date_obj.strftime("%Y-%m")
            elif group_by == "week":
                period_key = date_obj.strftime("%Y-W%U")
            else:  # day
                period_key = date_obj.strftime("%Y-%m-%d")
        except:
            continue
        
        amount = txn.get("amount", 0)
        
        # Get category type
        category_id = txn.get("category_id")
        category_type = None
        if category_id:
            category = await db.categories.find_one({"id": category_id})
            if category:
                category_type = category.get("type")
        
        # Map to appropriate category
        if category_type == "INCOME":
            grouped_data[period_key]["income"] += amount
        elif category_type == "EXPENSE":
            grouped_data[period_key]["expense"] += amount
        elif category_type == "TRANSFER_INTERNAL_IN":
            grouped_data[period_key]["transfer_internal_in"] += amount
        elif category_type == "TRANSFER_INTERNAL_OUT":
            grouped_data[period_key]["transfer_internal_out"] += amount
        elif category_type == "TRANSFER_EXTERNAL_IN":
            grouped_data[period_key]["transfer_external_in"] += amount
        elif category_type == "TRANSFER_EXTERNAL_OUT":
            grouped_data[period_key]["transfer_external_out"] += amount
    
    # Convert to sorted list
    result = []
    for period, data in sorted(grouped_data.items()):
        result.append({
            "period": period,
            "income": round(data["income"], 2),
            "expense": round(data["expense"], 2),
            "net": round(data["income"] - data["expense"], 2),
            "transfer_internal_in": round(data["transfer_internal_in"], 2),
            "transfer_internal_out": round(data["transfer_internal_out"], 2),
            "transfer_external_in": round(data["transfer_external_in"], 2),
            "transfer_external_out": round(data["transfer_external_out"], 2)
        })
    
    return result

# Import History
@api_router.get("/imports", response_model=List[ImportBatch])
async def get_import_history(user_id: str = Depends(get_current_user)):
    batches = await db.import_batches.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("imported_at", -1).limit(50).to_list(50)
    return batches

# Delete All Transactions (Danger Zone)
@api_router.post("/transactions/delete-all")
async def delete_all_transactions(
    request: DeleteAllTransactionsRequest,
    user_id: str = Depends(get_current_user)
):
    # Verify confirmation text FIRST - regardless of transaction count
    if request.confirmation_text.strip().upper() != "DELETE ALL":
        raise HTTPException(status_code=400, detail="Confirmation text does not match. Please type 'DELETE ALL'")
    
    # Count transactions before deletion
    count = await db.transactions.count_documents({"user_id": user_id})
    
    if count == 0:
        return {"message": "No transactions to delete", "deleted_count": 0}
    
    # Delete all transactions for this user
    result = await db.transactions.delete_many({"user_id": user_id})
    
    # Also delete import batches
    await db.import_batches.delete_many({"user_id": user_id})
    
    logging.warning(f"User {user_id} deleted all {result.deleted_count} transactions")
    
    return {
        "message": f"Successfully deleted all transactions",
        "deleted_count": result.deleted_count
    }

# Debug endpoint to check data consistency
@api_router.get("/debug/data-check")
async def debug_data_check(user_id: str = Depends(get_current_user)):
    """
    Debug endpoint to check data consistency between transactions and categories
    """
    # Get all transactions
    transactions = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(10000)
    
    # Get all categories (system + user)
    categories = await db.categories.find(
        {"$or": [{"is_system": True}, {"user_id": user_id}]},
        {"_id": 0}
    ).to_list(1000)
    
    # Get category IDs from transactions
    txn_category_ids = set(txn.get("category_id") for txn in transactions if txn.get("category_id"))
    
    # Get available category IDs
    available_category_ids = set(cat["id"] for cat in categories)
    
    # Find orphaned transactions
    orphaned_category_ids = txn_category_ids - available_category_ids
    
    # Count by type
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

# Settings - Backup and Restore
@api_router.get("/settings/backup")
async def backup_database(user_id: str = Depends(get_current_user)):
    """
    Create a backup of all user data (transactions, categories, rules, accounts, imports)
    Returns a ZIP file containing JSON data
    """
    import zipfile
    from io import BytesIO
    
    try:
        # Collect all user data
        transactions = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(10000)
        
        # Get ALL categories (system + user) that user's data references
        # This ensures transactions and rules have valid category references
        categories = await db.categories.find(
            {"$or": [{"is_system": True}, {"user_id": user_id}]},
            {"_id": 0}
        ).to_list(1000)
        
        rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        accounts = await db.accounts.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        import_batches = await db.import_batches.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        
        # Create ZIP file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add each collection as a JSON file
            zip_file.writestr('transactions.json', json.dumps(transactions, indent=2, default=str))
            zip_file.writestr('categories.json', json.dumps(categories, indent=2, default=str))
            zip_file.writestr('rules.json', json.dumps(rules, indent=2, default=str))
            zip_file.writestr('accounts.json', json.dumps(accounts, indent=2, default=str))
            zip_file.writestr('import_batches.json', json.dumps(import_batches, indent=2, default=str))
            
            # Add metadata
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
        
        # Prepare response
        zip_buffer.seek(0)
        
        # Generate filename with domain and timestamp
        domain = os.environ.get('DOMAIN', 'localhost')
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"SpendAlizer-{domain}-{timestamp}.zip"
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logging.error(f"Backup failed for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

class RestoreRequest(BaseModel):
    file: str  # Base64 encoded ZIP file content

@api_router.post("/settings/restore")
async def restore_database(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    """
    Restore database from a backup file
    1. Create backup of current data
    2. Flush current user data
    3. Restore from uploaded backup
    """
    import zipfile
    from io import BytesIO
    
    try:
        # Step 1: Create backup of current data first
        logging.info(f"Creating pre-restore backup for user {user_id}")
        current_transactions = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(10000)
        current_categories = await db.categories.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        current_rules = await db.category_rules.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        current_accounts = await db.accounts.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        current_imports = await db.import_batches.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
        
        # Create pre-restore backup ZIP
        pre_restore_buffer = BytesIO()
        with zipfile.ZipFile(pre_restore_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('transactions.json', json.dumps(current_transactions, indent=2, default=str))
            zip_file.writestr('categories.json', json.dumps(current_categories, indent=2, default=str))
            zip_file.writestr('rules.json', json.dumps(current_rules, indent=2, default=str))
            zip_file.writestr('accounts.json', json.dumps(current_accounts, indent=2, default=str))
            zip_file.writestr('import_batches.json', json.dumps(current_imports, indent=2, default=str))
            
            metadata = {
                "backup_date": datetime.now(timezone.utc).isoformat(),
                "backup_type": "pre_restore",
                "user_id": user_id
            }
            zip_file.writestr('metadata.json', json.dumps(metadata, indent=2))
        
        # Save pre-restore backup to disk (optional - for safety)
        backup_dir = Path("/tmp/spendalizer_backups")
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = backup_dir / f"pre_restore_{user_id}_{timestamp}.zip"
        with open(backup_path, 'wb') as f:
            f.write(pre_restore_buffer.getvalue())
        logging.info(f"Pre-restore backup saved to {backup_path}")
        
        # Step 2: Read and validate uploaded backup file
        content = await file.read()
        zip_buffer = BytesIO(content)
        
        try:
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                # Verify ZIP structure
                required_files = ['transactions.json', 'categories.json', 'rules.json', 'accounts.json', 'metadata.json']
                zip_files = zip_file.namelist()
                
                for req_file in required_files:
                    if req_file not in zip_files:
                        raise HTTPException(status_code=400, detail=f"Invalid backup file: missing {req_file}")
                
                # Read metadata
                metadata_content = zip_file.read('metadata.json')
                metadata = json.loads(metadata_content)
                
                # Read all data
                transactions_data = json.loads(zip_file.read('transactions.json'))
                categories_data = json.loads(zip_file.read('categories.json'))
                rules_data = json.loads(zip_file.read('rules.json'))
                accounts_data = json.loads(zip_file.read('accounts.json'))
                import_batches_data = json.loads(zip_file.read('import_batches.json')) if 'import_batches.json' in zip_files else []
                
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON in backup file: {str(e)}")
        
        # Step 3: Flush current user data
        # Note: System categories are global (shared by all users) and cannot be flushed
        # Only user-specific data is deleted
        logging.info(f"Flushing current data for user {user_id}")
        await db.transactions.delete_many({"user_id": user_id})
        await db.categories.delete_many({"user_id": user_id})  # Only user categories
        await db.category_rules.delete_many({"user_id": user_id})
        await db.accounts.delete_many({"user_id": user_id})
        await db.import_batches.delete_many({"user_id": user_id})
        
        # Step 4: Restore data
        # Since system categories now have consistent IDs across environments (from git),
        # we can restore everything directly without mapping
        logging.info(f"Restoring data for user {user_id}")
        restored_counts = {
            "transactions": 0,
            "categories": 0,
            "rules": 0,
            "accounts": 0,
            "import_batches": 0
        }
        
        # Restore categories (only user categories, system categories already exist with same IDs)
        if categories_data:
            for cat in categories_data:
                if not cat.get("is_system"):
                    # User category: restore with same ID
                    cat["user_id"] = user_id
                    await db.categories.insert_one(cat)
                    restored_counts["categories"] += 1
                # System categories are skipped - they already exist with same IDs
        
        # Restore transactions (no mapping needed - category IDs are consistent)
        if transactions_data:
            for txn in transactions_data:
                txn["user_id"] = user_id
            await db.transactions.insert_many(transactions_data)
            restored_counts["transactions"] = len(transactions_data)
        
        # Restore rules (no mapping needed)
        if rules_data:
            for rule in rules_data:
                rule["user_id"] = user_id
            await db.category_rules.insert_many(rules_data)
            restored_counts["rules"] = len(rules_data)
        
        # Restore accounts
        if accounts_data:
            for acc in accounts_data:
                acc["user_id"] = user_id
            await db.accounts.insert_many(accounts_data)
            restored_counts["accounts"] = len(accounts_data)
        
        # Restore import batches
        if import_batches_data:
            for batch in import_batches_data:
                batch["user_id"] = user_id
            await db.import_batches.insert_many(import_batches_data)
            restored_counts["import_batches"] = len(import_batches_data)
        
        logging.info(f"Restore completed for user {user_id}: {restored_counts}")
        
        # Get current user info
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
