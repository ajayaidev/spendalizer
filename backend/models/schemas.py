"""Pydantic models/schemas for the application."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, EmailStr

from models.enums import AccountType, TransactionDirection, CategorisationSource, MatchType, ImportStatus


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
    delete_transactions: bool = True
    delete_categories: bool = False
    delete_system_categories: bool = False
    delete_rules: bool = False
    delete_accounts: bool = False
    delete_imports: bool = False


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


class CategoryUpdate(BaseModel):
    category_id: str


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


class BulkCategoryUpdate(BaseModel):
    transaction_ids: List[str]
    category_id: str


class BulkRuleCategorize(BaseModel):
    transaction_ids: List[str]


class RestoreRequest(BaseModel):
    file: str  # Base64 encoded ZIP file content
