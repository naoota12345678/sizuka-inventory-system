from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import pytz
import os
from supabase import create_client, Client

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
    """既存システムの動作状況を診断"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        status = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "overall_status": "checking",
            "components": {}
        }
        
        # 1. データベース接続確認
        try:
            response = supabase.table('inventory').select('count').limit(1).execute()
            status["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection working"
            }
        except Exception as e:
            status["components"]["database"] = {
                "status": "error",
                "message": f"Database connection failed: {str(e)}"
            }
        
        # 2. 製造データ確認（最近のデータがあるか）
        try:
            recent_production = supabase.table('production_log').select('*').order('created_at', desc=True).limit(5).execute()
            if recent_production.data:
                last_production = recent_production.data[0]['created_at']
                status["components"]["production_system"] = {
                    "status": "healthy" if recent_production.data else "warning",
                    "message": f"Last production entry: {last_production}",
                    "recent_entries": len(recent_production.data)
                }
            else:
                status["components"]["production_system"] = {
                    "status": "warning",
                    "message": "No production data found",
                    "recent_entries": 0
                }
        except Exception as e:
            status["components"]["production_system"] = {
                "status": "error",
                "message": f"Production system check failed: {str(e)}"
            }
        
        # 3. 楽天売上データ確認
        try:
            recent_orders = supabase.table('orders').select('*').order('created_at', desc=True).limit(5).execute()
            if recent_orders.data:
                last_order = recent_orders.data[0]['created_at']
                status["components"]["rakuten_system"] = {
                    "status": "healthy",
                    "message": f"Last order sync: {last_order}",
                    "recent_orders": len(recent_orders.data)
                }
            else:
                status["components"]["rakuten_system"] = {
                    "status": "warning",
                    "message": "No order data found",
                    "recent_orders": 0
                }
        except Exception as e:
            status["components"]["rakuten_system"] = {
                "status": "error",
                "message": f"Rakuten system check failed: {str(e))"
            }
        
        # 4. 在庫データ確認
        try:
            inventory_count = supabase.table('inventory').select('count').execute()
            low_stock = supabase.table('inventory').select('*').lte('current_stock', 'minimum_stock').execute()
            
            status["components"]["inventory_system"] = {
                "status": "healthy",
                "total_products": len(inventory_count.data) if inventory_count.data else 0,
                "low_stock_items": len(low_stock.data) if low_stock.data else 0
            }
        except Exception as e:
            status["components"]["inventory_system"] = {
                "status": "error",
                "message": f"Inventory system check failed: {str(e)}"
            }
        
        # 5. 名寄せリスト確認
        try:
            mapping_data = supabase.table('product_mapping').select('*').limit(5).execute()
            status["components"]["product_mapping"] = {
                "status": "healthy" if mapping_data.data else "warning",
                "mapped_products": len(mapping_data.data) if mapping_data.data else 0,
                "message": "Product mapping table exists" if mapping_data.data else "No product mapping found"
            }
        except Exception as e:
            status["components"]["product_mapping"] = {
                "status": "error",
                "message": f"Product mapping check failed: {str(e)}"
            }
        
        # 全体ステータス判定
        component_statuses = [comp["status"] for comp in status["components"].values()]
        if "error" in component_statuses:
            status["overall_status"] = "error"
        elif "warning" in component_statuses:
            status["overall_status"] = "warning"
        else:
            status["overall_status"] = "healthy"
        
        return status
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": f"System status check failed: {str(e)}",
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )