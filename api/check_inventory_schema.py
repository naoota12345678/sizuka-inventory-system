from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
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

@app.get("/api/check_inventory_schema")
async def check_inventory_schema():
    """inventoryテーブルの構造を確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # テーブルの全データを1件取得してカラム構造を確認
        try:
            response = supabase.table('inventory').select('*').limit(1).execute()
            
            schema_info = {
                "status": "success",
                "table_exists": True,
                "sample_data": response.data[0] if response.data else None,
                "columns": list(response.data[0].keys()) if response.data else [],
                "record_count": len(response.data) if response.data else 0,
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
            
            return schema_info
            
        except Exception as table_error:
            return {
                "status": "error",  
                "table_exists": False,
                "error_message": str(table_error),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

@app.get("/api/check_all_tables")
async def check_all_tables():
    """主要テーブルの構造を確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        tables_to_check = ['inventory', 'product_master', 'sales_daily', 'orders', 'platform']
        
        results = {
            "status": "success",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "tables": {}
        }
        
        for table_name in tables_to_check:
            try:
                response = supabase.table(table_name).select('*').limit(1).execute()
                
                results["tables"][table_name] = {
                    "exists": True,
                    "columns": list(response.data[0].keys()) if response.data else [],
                    "sample_count": len(response.data) if response.data else 0,
                    "sample_data": response.data[0] if response.data else None
                }
                
            except Exception as e:
                results["tables"][table_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        return results
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )