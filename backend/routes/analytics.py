"""Analytics routes."""
from collections import defaultdict
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends

from database import db
from auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
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
    
    # Get all categories to determine their types
    all_categories = await db.categories.find(
        {"$or": [{"is_system": True}, {"user_id": user_id}]},
        {"_id": 0}
    ).to_list(1000)
    category_map = {cat["id"]: cat for cat in all_categories}
    
    # Calculate income/expense excluding TRANSFER categories
    total_income = 0
    total_expense = 0
    total_transfer_in = 0
    total_transfer_out = 0
    
    for txn in transactions:
        amount = txn["amount"]
        direction = txn["direction"]
        cat_id = txn.get("category_id")
        
        # Check if this is a TRANSFER category
        cat_type = None
        if cat_id and cat_id in category_map:
            cat_type = category_map[cat_id].get("type", "")
        
        is_transfer = cat_type and "TRANSFER" in cat_type
        
        if is_transfer:
            # Don't count transfers as income/expense
            if "IN" in cat_type or direction == "CREDIT":
                total_transfer_in += amount
            else:
                total_transfer_out += amount
        else:
            # Regular income/expense based on direction
            if direction == "CREDIT":
                total_income += amount
            else:
                total_expense += amount
    
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
            uncategorized_total += txn["amount"]
            uncategorized_count += 1
    
    # category_map already loaded above
    
    enriched_breakdown = []
    for cat_id, data in category_breakdown.items():
        category = category_map.get(cat_id)
        if category:
            cat_type = category["type"]
            
            if cat_type in ["TRANSFER_INTERNAL_IN", "TRANSFER_EXTERNAL_IN"]:
                incoming_total = sum(txn["amount"] for txn in transactions if txn.get("category_id") == cat_id)
                incoming_count = len([txn for txn in transactions if txn.get("category_id") == cat_id])
                if incoming_count > 0:
                    enriched_breakdown.append({
                        "category_id": cat_id,
                        "category_name": category["name"],
                        "category_type": cat_type,
                        "total": incoming_total,
                        "count": incoming_count
                    })
            elif cat_type in ["TRANSFER_INTERNAL_OUT", "TRANSFER_EXTERNAL_OUT"]:
                outgoing_total = sum(txn["amount"] for txn in transactions if txn.get("category_id") == cat_id)
                outgoing_count = len([txn for txn in transactions if txn.get("category_id") == cat_id])
                if outgoing_count > 0:
                    enriched_breakdown.append({
                        "category_id": cat_id,
                        "category_name": category["name"],
                        "category_type": cat_type,
                        "total": outgoing_total,
                        "count": outgoing_count
                    })
            elif cat_type in ["TRANSFER", "TRANSFER_INTERNAL", "TRANSFER_EXTERNAL"]:
                incoming_total = sum(txn["amount"] for txn in transactions if txn.get("category_id") == cat_id and txn["direction"] == "CREDIT")
                incoming_count = sum(1 for txn in transactions if txn.get("category_id") == cat_id and txn["direction"] == "CREDIT")
                outgoing_total = sum(txn["amount"] for txn in transactions if txn.get("category_id") == cat_id and txn["direction"] == "DEBIT")
                outgoing_count = sum(1 for txn in transactions if txn.get("category_id") == cat_id and txn["direction"] == "DEBIT")
                
                if cat_type == "TRANSFER_INTERNAL":
                    display_type_in, display_type_out = "TRANSFER_INTERNAL_IN", "TRANSFER_INTERNAL_OUT"
                elif cat_type == "TRANSFER_EXTERNAL":
                    display_type_in, display_type_out = "TRANSFER_EXTERNAL_IN", "TRANSFER_EXTERNAL_OUT"
                else:
                    display_type_in, display_type_out = "TRANSFER_IN", "TRANSFER_OUT"
                
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
        "total_transfer_in": round(total_transfer_in, 2),
        "total_transfer_out": round(total_transfer_out, 2),
        "transaction_count": len(transactions),
        "category_breakdown": sorted(enriched_breakdown, key=lambda x: x["total"], reverse=True)
    }


@router.get("/spending-over-time")
async def get_spending_over_time(
    user_id: str = Depends(get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "month"
):
    query = {"user_id": user_id}
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        query.setdefault("date", {})["$lte"] = end_date
    
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(10000)
    
    grouped_data = defaultdict(lambda: {
        "income": 0, "expense": 0,
        "transfer_internal_in": 0, "transfer_internal_out": 0,
        "transfer_external_in": 0, "transfer_external_out": 0
    })
    
    for txn in transactions:
        date_str = txn.get("date", "")
        if not date_str:
            continue
        
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if group_by == "month":
                period_key = date_obj.strftime("%Y-%m")
            elif group_by == "week":
                period_key = date_obj.strftime("%Y-W%U")
            else:
                period_key = date_obj.strftime("%Y-%m-%d")
        except:
            continue
        
        amount = txn.get("amount", 0)
        category_id = txn.get("category_id")
        category_type = None
        
        if category_id:
            category = await db.categories.find_one({"id": category_id})
            if category:
                category_type = category.get("type")
        
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


@router.get("/category-trends")
async def get_category_trends(
    user_id: str = Depends(get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "month"
):
    query = {"user_id": user_id}
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        query.setdefault("date", {})["$lte"] = end_date
    
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(10000)
    categories = await db.categories.find(
        {"$or": [{"is_system": True}, {"user_id": user_id}]},
        {"_id": 0}
    ).to_list(1000)
    
    category_map = {cat["id"]: cat for cat in categories}
    
    period_category_data = defaultdict(lambda: defaultdict(float))
    category_totals = defaultdict(float)
    
    for txn in transactions:
        date_str = txn.get("date", "")
        if not date_str:
            continue
        
        try:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if group_by == "month":
                period_key = date_obj.strftime("%Y-%m")
            elif group_by == "week":
                period_key = date_obj.strftime("%Y-W%U")
            else:
                period_key = date_obj.strftime("%Y-%m-%d")
        except:
            continue
        
        category_id = txn.get("category_id")
        amount = txn.get("amount", 0)
        
        if category_id and category_id in category_map:
            period_category_data[period_key][category_id] += amount
            category_totals[category_id] += amount
    
    result = {
        "periods": sorted(period_category_data.keys()),
        "categories": [],
        "data": {}
    }
    
    category_groups = {
        "INCOME": [], "EXPENSE": [],
        "TRANSFER_INTERNAL_IN": [], "TRANSFER_INTERNAL_OUT": [],
        "TRANSFER_EXTERNAL_IN": [], "TRANSFER_EXTERNAL_OUT": []
    }
    
    for cat_id, category in category_map.items():
        if category_totals.get(cat_id, 0) > 0:
            cat_type = category.get("type", "")
            if cat_type in category_groups:
                category_groups[cat_type].append({
                    "id": cat_id,
                    "name": category["name"],
                    "type": cat_type,
                    "total": round(category_totals[cat_id], 2)
                })
    
    for group_type, cats in category_groups.items():
        if cats:
            result["categories"].extend(sorted(cats, key=lambda x: x["name"]))
    
    for period in result["periods"]:
        result["data"][period] = {}
        for cat_id in category_totals.keys():
            if category_totals[cat_id] > 0:
                result["data"][period][cat_id] = round(period_category_data[period].get(cat_id, 0), 2)
    
    return result
