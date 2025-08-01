from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import pytz
import os
import traceback

app = FastAPI()

@app.get("/api/inventory_list")
async def get_inventory_list():
    """在庫一覧を取得"""
    try:
        # 環境変数チェック
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "error",
                    "message": "Database credentials not configured",
                    "has_url": bool(SUPABASE_URL),
                    "has_key": bool(SUPABASE_KEY),
                    "items": []
                }
            )
        
        # Supabase接続を試みる
        try:
            from supabase import create_client, Client
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as conn_error:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "error",
                    "message": f"Database connection error: {str(conn_error)}",
                    "items": []
                }
            )
        
        # データ取得を試みる
        try:
            response = supabase.table('inventory').select('*').limit(20).execute()
            
            return {
                "status": "success",
                "count": len(response.data) if response.data else 0,
                "items": response.data if response.data else [],
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        except Exception as query_error:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "error",
                    "message": f"Query error: {str(query_error)}",
                    "items": []
                }
            )
            
    except Exception as e:
        # 予期しないエラー
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )