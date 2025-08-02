#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
実際のorder_itemsデータ確認API
"""

from fastapi import FastAPI
from core.database import supabase
import json

app = FastAPI()

@app.get("/api/check_real_order_items")
async def check_real_order_items():
    """order_itemsテーブルの実際のデータを確認"""
    try:
        # 1. 総件数
        count_response = supabase.table("order_items").select("id", count="exact").execute()
        total_count = len(count_response.data) if count_response.data else 0
        
        # 2. 最新10件
        latest_response = supabase.table("order_items").select("*").order("created_at", desc=True).limit(10).execute()
        latest_items = latest_response.data if latest_response.data else []
        
        # 3. 日付範囲確認（ordersテーブルと結合）
        date_response = supabase.table("order_items").select("""
            id, created_at, product_code, product_name, rakuten_sku, choice_code,
            orders!inner(order_date, order_number)
        """).order("orders.order_date", desc=True).execute()
        
        date_items = date_response.data if date_response.data else []
        
        # 日付の集計
        dates = []
        monthly_count = {}
        sku_count = 0
        choice_count = 0
        
        for item in date_items:
            if item.get('orders') and item['orders'].get('order_date'):
                order_date = item['orders']['order_date']
                dates.append(order_date)
                month = order_date[:7]  # YYYY-MM
                monthly_count[month] = monthly_count.get(month, 0) + 1
            
            if item.get('rakuten_sku'):
                sku_count += 1
            if item.get('choice_code'):
                choice_count += 1
        
        dates.sort()
        
        return {
            "status": "success",
            "summary": {
                "total_records": total_count,
                "sku_registered": sku_count,
                "choice_code_registered": choice_count,
                "date_range": {
                    "oldest": dates[0] if dates else None,
                    "newest": dates[-1] if dates else None
                },
                "monthly_distribution": dict(sorted(monthly_count.items()))
            },
            "latest_10_samples": [
                {
                    "created_at": item.get("created_at"),
                    "product_code": item.get("product_code"),
                    "product_name": item.get("product_name", "")[:50] + "...",
                    "rakuten_sku": item.get("rakuten_sku", "なし"),
                    "choice_code": item.get("choice_code", "なし"),
                    "quantity": item.get("quantity", 0),
                    "price": item.get("price", 0)
                }
                for item in latest_items[:10]
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }