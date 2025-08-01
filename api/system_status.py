from fastapi import FastAPI, Query
from datetime import datetime
import pytz
import os
from supabase import create_client, Client
from typing import Optional

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/system_status")
async def get_system_status():
    """簡易システム診断"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        status = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "database_connected": True,
            "tables_status": {}
        }
        
        # 実際のテーブル名をチェック
        tables_to_check = [
            'inventory',           # 在庫管理テーブル
            'orders',             # 楽天注文テーブル
            'order_items',        # 楽天注文商品テーブル
            'sales_daily',        # 日別売上テーブル
            'platform',           # プラットフォーム管理
            'product_master',     # 商品マスター
            'unified_products',   # 統合商品マスター
            'sales_transactions', # 売上取引テーブル
            'inventory_transactions' # 在庫取引テーブル
        ]
        
        for table_name in tables_to_check:
            try:
                result = supabase.table(table_name).select('count').limit(1).execute()
                status["tables_status"][table_name] = {
                    "exists": True,
                    "has_data": len(result.data) > 0 if result.data else False
                }
            except Exception as e:
                status["tables_status"][table_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        # 在庫データの基本情報
        try:
            inventory_result = supabase.table('inventory').select('*').limit(10).execute()
            status["inventory_sample"] = {
                "count": len(inventory_result.data) if inventory_result.data else 0,
                "sample": inventory_result.data[:3] if inventory_result.data else []
            }
        except Exception as e:
            status["inventory_sample"] = {"error": str(e)}
        
        # 注文データの基本情報
        try:
            orders_result = supabase.table('orders').select('*').order('created_at', desc=True).limit(5).execute()
            status["orders_sample"] = {
                "count": len(orders_result.data) if orders_result.data else 0,
                "latest": orders_result.data[0] if orders_result.data else None
            }
        except Exception as e:
            status["orders_sample"] = {"error": str(e)}
        
        return status
        
    except Exception as e:
        return {
            "error": f"System check failed: {str(e)}",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/debug_inventory")
async def debug_inventory():
    """inventoryテーブルの構造確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        response = supabase.table('inventory').select('*').limit(3).execute()
        
        return {
            "status": "success",
            "record_count": len(response.data) if response.data else 0,
            "columns": list(response.data[0].keys()) if response.data else [],
            "sample_data": response.data[0] if response.data else None,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }