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

@app.get("/api/debug_inventory_table")
async def debug_inventory_table():
    """inventoryテーブルの構造と内容を詳細確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        debug_info = {
            "status": "success",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "table_info": {}
        }
        
        # 1. inventoryテーブルの全データを取得（最大10件）
        try:
            response = supabase.table('inventory').select('*').limit(10).execute()
            
            if response.data and len(response.data) > 0:
                sample_record = response.data[0]
                debug_info["table_info"] = {
                    "exists": True,
                    "record_count": len(response.data),
                    "columns": list(sample_record.keys()),
                    "sample_records": response.data,
                    "column_analysis": {}
                }
                
                # 各カラムの内容を分析
                for column_name in sample_record.keys():
                    values = [str(record.get(column_name, '')) for record in response.data[:5]]
                    debug_info["table_info"]["column_analysis"][column_name] = {
                        "sample_values": values,
                        "data_type": type(sample_record[column_name]).__name__ if sample_record[column_name] is not None else "null"
                    }
                
            else:
                debug_info["table_info"] = {
                    "exists": True,
                    "record_count": 0,
                    "columns": [],
                    "message": "テーブルは存在するがデータが空です"
                }
                
        except Exception as table_error:
            debug_info["table_info"] = {
                "exists": False,
                "error": str(table_error)
            }
        
        # 2. 他の関連テーブルも確認
        other_tables = ['product_master', 'sales_daily', 'orders']
        debug_info["related_tables"] = {}
        
        for table_name in other_tables:
            try:
                response = supabase.table(table_name).select('*').limit(3).execute()
                debug_info["related_tables"][table_name] = {
                    "exists": True,
                    "record_count": len(response.data) if response.data else 0,
                    "columns": list(response.data[0].keys()) if response.data else [],
                    "sample": response.data[0] if response.data else None
                }
            except Exception as e:
                debug_info["related_tables"][table_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        return debug_info
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

@app.post("/api/test_inventory_insert")
async def test_inventory_insert():
    """テスト用の在庫データ挿入"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # テスト用データ
        test_data = {
            "product_name": "テスト商品",
            "current_stock": 10,
            "minimum_stock": 5,
            "unit": "個",
            "unit_price": 800,
            "category": "テスト",
            "created_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        # 挿入テスト
        response = supabase.table('inventory').insert(test_data).execute()
        
        return {
            "status": "success",
            "message": "テストデータの挿入に成功しました",
            "inserted_data": response.data,
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