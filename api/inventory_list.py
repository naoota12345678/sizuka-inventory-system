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

@app.get("/api/inventory_list")
async def get_inventory_list():
    """在庫一覧を取得"""
    try:
        if not supabase:
            return {"error": "Database connection not configured", "items": []}
        
        response = supabase.table('inventory').select('*').limit(20).execute()
        
        return {
            "status": "success",
            "count": len(response.data),
            "items": response.data,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )