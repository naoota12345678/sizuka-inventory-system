#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazon売上ダッシュボードAPI
期間指定可能な売上集計機能
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from supabase import create_client
import logging
from collections import defaultdict
import os

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続情報
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://equrcpeifogdrxoldkpe.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ")

app = FastAPI(title="Amazon売上分析API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "Amazon Sales Dashboard API", "version": "1.0.0"}

@app.get("/api/amazon/sales/dashboard")
async def get_sales_dashboard(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Amazon売上ダッシュボードデータを取得
    
    Args:
        start_date: 開始日
        end_date: 終了日
        
    Returns:
        ダッシュボードデータ
    """
    try:
        # デフォルト期間設定（過去30日）
        if not end_date:
            end_date = date.today().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
            
        logger.info(f"Fetching Amazon sales data from {start_date} to {end_date}")
        
        # 注文データを取得
        orders_query = supabase.table("amazon_orders").select("*").gte("purchase_date", start_date).lte("purchase_date", end_date)
        orders_response = orders_query.execute()
        orders = orders_response.data if orders_response.data else []
        
        # 注文IDのリストを作成
        order_ids = [order["id"] for order in orders]
        
        if not order_ids:
            return {
                "period": {"start": start_date, "end": end_date},
                "summary": {
                    "total_sales": 0,
                    "total_orders": 0,
                    "total_items": 0,
                    "average_order_value": 0
                },
                "daily_sales": [],
                "top_products": [],
                "fulfillment_breakdown": {},
                "marketplace_breakdown": {}
            }
            
        # 注文商品データを取得
        items_query = supabase.table("amazon_order_items").select("*").in_("order_id", order_ids)
        items_response = items_query.execute()
        items = items_response.data if items_response.data else []
        
        # 集計処理
        total_sales = 0
        total_items = 0
        daily_sales = defaultdict(lambda: {"sales": 0, "orders": 0, "items": 0})
        product_sales = defaultdict(lambda: {"quantity": 0, "sales": 0, "product_name": ""})
        fulfillment_breakdown = defaultdict(lambda: {"orders": 0, "sales": 0})
        marketplace_breakdown = defaultdict(lambda: {"orders": 0, "sales": 0})
        
        # 注文ごとの処理
        for order in orders:
            order_date = order["purchase_date"][:10]  # YYYY-MM-DD形式
            order_total = float(order.get("order_total", 0))
            
            daily_sales[order_date]["orders"] += 1
            daily_sales[order_date]["sales"] += order_total
            
            fulfillment = order.get("fulfillment_channel", "Unknown")
            fulfillment_breakdown[fulfillment]["orders"] += 1
            fulfillment_breakdown[fulfillment]["sales"] += order_total
            
            marketplace = order.get("marketplace_id", "Unknown")
            marketplace_breakdown[marketplace]["orders"] += 1
            marketplace_breakdown[marketplace]["sales"] += order_total
            
            total_sales += order_total
            
        # 商品ごとの処理
        for item in items:
            sku = item.get("sku", "Unknown")
            quantity = item.get("quantity_ordered", 0)
            item_price = float(item.get("item_price", 0))
            product_name = item.get("product_name", sku)
            
            product_sales[sku]["quantity"] += quantity
            product_sales[sku]["sales"] += item_price
            product_sales[sku]["product_name"] = product_name
            
            order_date = next((o["purchase_date"][:10] for o in orders if o["id"] == item["order_id"]), None)
            if order_date:
                daily_sales[order_date]["items"] += quantity
                
            total_items += quantity
            
        # 日別売上をリスト形式に変換
        daily_sales_list = [
            {
                "date": date_str,
                "sales": round(data["sales"], 2),
                "orders": data["orders"],
                "items": data["items"]
            }
            for date_str, data in sorted(daily_sales.items())
        ]
        
        # トップ商品をリスト形式に変換（売上高順）
        top_products = [
            {
                "sku": sku,
                "product_name": data["product_name"],
                "quantity": data["quantity"],
                "sales": round(data["sales"], 2)
            }
            for sku, data in sorted(product_sales.items(), key=lambda x: x[1]["sales"], reverse=True)[:10]
        ]
        
        # レスポンス作成
        response = {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "summary": {
                "total_sales": round(total_sales, 2),
                "total_orders": len(orders),
                "total_items": total_items,
                "average_order_value": round(total_sales / len(orders), 2) if orders else 0
            },
            "daily_sales": daily_sales_list,
            "top_products": top_products,
            "fulfillment_breakdown": dict(fulfillment_breakdown),
            "marketplace_breakdown": dict(marketplace_breakdown)
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in sales dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/amazon/sales/products")
async def get_product_sales(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    limit: int = Query(50, description="取得件数上限")
) -> List[Dict[str, Any]]:
    """
    商品別売上一覧を取得
    
    Args:
        start_date: 開始日
        end_date: 終了日
        limit: 取得件数上限
        
    Returns:
        商品別売上データ
    """
    try:
        # デフォルト期間設定
        if not end_date:
            end_date = date.today().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
            
        # 注文データを取得
        orders_query = supabase.table("amazon_orders").select("id, purchase_date").gte("purchase_date", start_date).lte("purchase_date", end_date)
        orders_response = orders_query.execute()
        orders = orders_response.data if orders_response.data else []
        
        order_ids = [order["id"] for order in orders]
        
        if not order_ids:
            return []
            
        # 注文商品データを取得
        items_query = supabase.table("amazon_order_items").select("*").in_("order_id", order_ids)
        items_response = items_query.execute()
        items = items_response.data if items_response.data else []
        
        # 商品ごとに集計
        product_data = defaultdict(lambda: {
            "product_name": "",
            "asin": "",
            "quantity": 0,
            "sales": 0,
            "orders": set()
        })
        
        for item in items:
            sku = item.get("sku", "Unknown")
            product_data[sku]["product_name"] = item.get("product_name", sku)
            product_data[sku]["asin"] = item.get("asin", "")
            product_data[sku]["quantity"] += item.get("quantity_ordered", 0)
            product_data[sku]["sales"] += float(item.get("item_price", 0))
            product_data[sku]["orders"].add(item.get("amazon_order_id"))
            
        # リスト形式に変換
        products_list = []
        for sku, data in product_data.items():
            # 共通コードを取得
            common_code = ""
            try:
                master_response = supabase.table("amazon_product_master").select("common_code").eq("sku", sku).execute()
                if master_response.data:
                    common_code = master_response.data[0].get("common_code", "")
            except:
                pass
                
            products_list.append({
                "sku": sku,
                "product_name": data["product_name"],
                "asin": data["asin"],
                "common_code": common_code,
                "quantity": data["quantity"],
                "sales": round(data["sales"], 2),
                "order_count": len(data["orders"]),
                "average_price": round(data["sales"] / data["quantity"], 2) if data["quantity"] > 0 else 0
            })
            
        # 売上高順にソート
        products_list.sort(key=lambda x: x["sales"], reverse=True)
        
        return products_list[:limit]
        
    except Exception as e:
        logger.error(f"Error in product sales: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/amazon/inventory/status")
async def get_inventory_status() -> Dict[str, Any]:
    """
    在庫状況サマリーを取得
    
    Returns:
        在庫状況データ
    """
    try:
        # FBA在庫を取得
        fba_response = supabase.table("amazon_fba_inventory").select("*").execute()
        fba_items = fba_response.data if fba_response.data else []
        
        # 在庫集計
        total_fba = 0
        total_inbound = 0
        low_stock_items = []
        
        for item in fba_items:
            fulfillable = item.get("fulfillable_quantity", 0)
            inbound = (
                item.get("inbound_working_quantity", 0) +
                item.get("inbound_shipped_quantity", 0) +
                item.get("inbound_receiving_quantity", 0)
            )
            
            total_fba += fulfillable
            total_inbound += inbound
            
            # 低在庫判定（10個以下）
            if fulfillable <= 10:
                low_stock_items.append({
                    "sku": item.get("sku"),
                    "product_name": item.get("product_name"),
                    "current_stock": fulfillable,
                    "inbound": inbound
                })
                
        return {
            "summary": {
                "total_fba_stock": total_fba,
                "total_inbound": total_inbound,
                "total_skus": len(set(item.get("sku") for item in fba_items)),
                "low_stock_count": len(low_stock_items)
            },
            "low_stock_items": low_stock_items[:20]  # 上位20件
        }
        
    except Exception as e:
        logger.error(f"Error in inventory status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/amazon/sales/comparison")
async def get_sales_comparison() -> Dict[str, Any]:
    """
    楽天とAmazonの売上比較データを取得
    
    Returns:
        プラットフォーム別売上比較
    """
    try:
        # 今月のデータを取得
        today = date.today()
        month_start = date(today.year, today.month, 1).strftime('%Y-%m-%d')
        month_end = today.strftime('%Y-%m-%d')
        
        # Amazon売上
        amazon_orders = supabase.table("amazon_orders").select("order_total").gte("purchase_date", month_start).lte("purchase_date", month_end).execute()
        amazon_total = sum(float(order.get("order_total", 0)) for order in (amazon_orders.data or []))
        
        # 楽天売上
        rakuten_items = supabase.table("order_items").select("quantity, price, orders(order_date)").gte("orders.order_date", month_start).lte("orders.order_date", month_end).execute()
        rakuten_total = sum(
            item.get("quantity", 0) * float(item.get("price", 0))
            for item in (rakuten_items.data or [])
            if item.get("orders")
        )
        
        total_sales = amazon_total + rakuten_total
        
        return {
            "period": {
                "start": month_start,
                "end": month_end
            },
            "platforms": {
                "amazon": {
                    "sales": round(amazon_total, 2),
                    "percentage": round((amazon_total / total_sales * 100), 1) if total_sales > 0 else 0
                },
                "rakuten": {
                    "sales": round(rakuten_total, 2),
                    "percentage": round((rakuten_total / total_sales * 100), 1) if total_sales > 0 else 0
                }
            },
            "total_sales": round(total_sales, 2)
        }
        
    except Exception as e:
        logger.error(f"Error in sales comparison: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)