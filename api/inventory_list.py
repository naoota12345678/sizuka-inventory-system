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

@app.get("/api/inventory_list")
async def get_inventory_list(
    page: Optional[int] = Query(1, description="ページ番号"),
    per_page: Optional[int] = Query(50, description="1ページあたりの件数"),
    sort_by: Optional[str] = Query("product_code", description="ソート項目"),
    sort_order: Optional[str] = Query("asc", description="ソート順序 (asc/desc)"),
    category: Optional[str] = Query(None, description="カテゴリフィルター"),
    status_filter: Optional[str] = Query(None, description="在庫状態フィルター (normal/low/out)")
):
    """在庫一覧取得API - 現在の在庫状況を表示"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 基本クエリ（まずテーブル構造を確認）
        query = supabase.table('inventory').select('*')
        
        # カテゴリフィルター
        if category:
            query = query.eq('category', category)
        
        # ソート設定
        query = query.order(sort_by, desc=(sort_order == 'desc'))
        
        # 全件取得して集計
        all_response = query.execute()
        all_items = all_response.data if all_response.data else []
        
        # 在庫状態でフィルタリング（クライアント側）
        if status_filter:
            filtered_items = []
            for item in all_items:
                current = item.get('current_stock', 0)
                minimum = item.get('minimum_stock', 0)
                
                if status_filter == 'out' and current == 0:
                    filtered_items.append(item)
                elif status_filter == 'low' and 0 < current <= minimum:
                    filtered_items.append(item)
                elif status_filter == 'normal' and current > minimum:
                    filtered_items.append(item)
            
            all_items = filtered_items
        
        # 統計情報を計算
        total_items = len(all_items)
        total_stock_value = 0
        out_of_stock = 0
        low_stock = 0
        normal_stock = 0
        
        for item in all_items:
            current = item.get('current_stock', 0)
            minimum = item.get('minimum_stock', 0)
            
            # 在庫金額（在庫数 × 単価）
            if item.get('unit_price'):
                total_stock_value += current * item.get('unit_price', 0)
            
            # 在庫状態カウント
            if current == 0:
                out_of_stock += 1
            elif current <= minimum:
                low_stock += 1
            else:
                normal_stock += 1
        
        # ページネーション
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_items = all_items[start_idx:end_idx]
        
        # 商品情報を整形（正しいテーブル構造に基づく）
        formatted_items = []
        for item in page_items:
            formatted_item = {
                "id": item.get('id'),
                "common_code": item.get('common_code'),  # 正しいフィールド名
                "product_name": item.get('product_name', '商品名未設定'),
                "current_stock": item.get('current_stock', 0),
                "initial_stock": item.get('initial_stock', 0),
                "minimum_stock": item.get('minimum_stock', 0),
                "reorder_point": item.get('reorder_point', 0),
                "status": get_stock_status(item.get('current_stock', 0), item.get('minimum_stock', 0)),
                "price": item.get('price'),
                "content": item.get('content', ''),  # 内容量
                "jan_code": item.get('jan_code'),
                "reference_date": item.get('reference_date'),
                "last_updated": item.get('last_updated'),
                "stock_value": item.get('current_stock', 0) * item.get('price', 0) if item.get('price') else None
            }
            formatted_items.append(formatted_item)
        
        # カテゴリ一覧を取得
        categories = list(set(item.get('category') for item in all_items if item.get('category')))
        
        return {
            "status": "success",
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": (total_items + per_page - 1) // per_page
            },
            "summary": {
                "total_products": total_items,
                "normal_stock": normal_stock,
                "low_stock": low_stock,
                "out_of_stock": out_of_stock,
                "total_stock_value": total_stock_value,
                "categories": categories
            },
            "items": formatted_items,
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

def get_stock_status(current: int, minimum: int) -> str:
    """在庫状態を判定"""
    if current == 0:
        return "out_of_stock"
    elif current <= minimum:
        return "low_stock"
    else:
        return "normal"

@app.post("/api/update_inventory_minimum")
async def update_inventory_minimum(
    item_id: str = Query(..., description="商品ID"),
    minimum_stock: int = Query(..., description="最小在庫数")
):
    """最小在庫数の更新（IDベース）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # IDで在庫レコードを更新
        response = supabase.table('inventory').update({
            "minimum_stock": minimum_stock,
            "updated_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }).eq('id', item_id).execute()
        
        if response.data:
            return {
                "status": "success",
                "message": f"商品ID {item_id} の最小在庫数を {minimum_stock} に更新しました",
                "data": response.data[0],
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        else:
            return {
                "status": "error",
                "message": f"商品ID {item_id} が見つかりません",
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