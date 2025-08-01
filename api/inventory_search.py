from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
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

@app.get("/api/inventory_search")
async def search_inventory(
    search: Optional[str] = Query(None, description="商品名または商品コードで検索"),
    low_stock: Optional[bool] = Query(False, description="在庫不足商品のみ表示"),
    min_stock: Optional[int] = Query(None, description="最小在庫数で絞り込み"),
    limit: Optional[int] = Query(20, description="取得件数")
):
    """在庫検索・フィルター機能（修正版）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured", "items": []}
        
        # 基本クエリ
        query = supabase.table('inventory').select('*')
        
        # 検索条件（修正版）
        if search:
            # 商品名で検索
            query = query.ilike('product_name', f'%{search}%')
        
        # 最小在庫数フィルター
        if min_stock is not None:
            query = query.lte('current_stock', min_stock)
        
        # 並び順：在庫の少ない順
        query = query.order('current_stock', desc=False)
        
        # 件数制限
        query = query.limit(limit)
        
        response = query.execute()
        
        # 在庫不足商品のフィルタリング（クライアント側で実行）
        items = response.data if response.data else []
        
        if low_stock:
            items = [item for item in items if item['current_stock'] <= item['minimum_stock']]
        
        # 在庫不足アラート
        alerts = []
        for item in items:
            if item['current_stock'] <= item['minimum_stock']:
                alerts.append({
                    "product_name": item['product_name'],
                    "current_stock": item['current_stock'],
                    "minimum_stock": item['minimum_stock'],
                    "shortage": item['minimum_stock'] - item['current_stock']
                })
        
        return {
            "status": "success",
            "search_params": {
                "search": search,
                "low_stock": low_stock,
                "min_stock": min_stock,
                "limit": limit
            },
            "count": len(items),
            "items": items,
            "alerts": alerts,
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