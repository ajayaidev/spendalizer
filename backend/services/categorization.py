"""Categorization engine for transactions."""
import json
import re
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import httpx

from database import db
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, ROOT_DIR


async def init_default_categories():
    """Initialize default categories from system_categories.json."""
    system_categories_path = ROOT_DIR / 'system_categories.json'
    
    try:
        with open(system_categories_path, 'r') as f:
            default_categories = json.load(f)
    except FileNotFoundError:
        logging.error(f"System categories file not found: {system_categories_path}")
        return
    
    for cat_data in default_categories:
        existing = await db.categories.find_one({"id": cat_data["id"]})
        if not existing:
            cat_data['created_at'] = datetime.now(timezone.utc).isoformat()
            await db.categories.insert_one(cat_data)
            logging.info(f"Initialized system category: {cat_data['name']} (id: {cat_data['id']})")
        else:
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


async def categorize_with_rules(user_id: str, description: str, account_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Try to categorize transaction using user-defined rules."""
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
    """Try to categorize transaction using LLM (Ollama)."""
    try:
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


async def categorize_transaction(user_id: str, description: str, amount: float, direction: str, transaction_type: str, account_id: Optional[str] = None) -> Dict[str, Any]:
    """Main categorization function - tries rules first, then LLM."""
    # First try rules
    rule_result = await categorize_with_rules(user_id, description, account_id)
    if rule_result:
        return rule_result
    
    # Then try LLM
    llm_result = await categorize_with_llm(
        description,
        amount,
        direction,
        transaction_type,
        user_id
    )
    if llm_result:
        return llm_result
    
    return {
        "category_id": None,
        "categorisation_source": "UNCATEGORISED",
        "confidence_score": None
    }


async def check_duplicate(user_id: str, account_id: str, date: str, amount: float, description: str) -> bool:
    """Check if a transaction already exists."""
    existing = await db.transactions.find_one({
        "user_id": user_id,
        "account_id": account_id,
        "date": date,
        "amount": amount,
        "description": description
    })
    return existing is not None
