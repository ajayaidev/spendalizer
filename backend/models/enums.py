"""Enumeration types for the application."""
from enum import Enum


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
