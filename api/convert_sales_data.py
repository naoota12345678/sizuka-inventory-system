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

@app.get("/api/convert_sales_data")
async def convert_sales_data():
    """既存の楽天注文データを売上データに変換（一時的な対応）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # sales_masterテーブルが存在するかチェック
        try:
            test_query = supabase.table('sales_master').select('count').limit(1).execute()
            table_exists = True
        except:
            table_exists = False
        
        if not table_exists:
            # sales_masterテーブルを作成（簡易版）
            return {
                "status": "error",
                "message": "sales_masterテーブルが存在しません。まずデータベースに以下のSQLを実行してください：",
                "sql": """
CREATE TABLE sales_master (
    id SERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    common_code VARCHAR(10) NOT NULL,
    platform_name VARCHAR(50) NOT NULL,
    platform_order_id VARCHAR(100),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    is_mapped BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sales_date_common ON sales_master(sale_date, common_code);
CREATE INDEX idx_sales_platform ON sales_master(platform_name);
"""
            }
        
        # 楽天注文データを取得
        orders = supabase.table('orders').select('*').execute()
        
        if not orders.data:
            return {
                "status": "warning",
                "message": "変換対象の注文データがありません"
            }
        
        converted_count = 0
        skipped_count = 0
        
        # 各注文を処理
        for order in orders.data:
            order_id = order['id']
            order_number = order.get('order_number')
            order_date = order.get('order_date', order.get('order_datetime', ''))[:10]
            
            # この注文の商品を取得
            order_items = supabase.table('order_items').select('*').eq('order_id', order_id).execute()
            
            if not order_items.data:
                continue
            
            for item in order_items.data:
                item_name = item.get('item_name', '')
                sku = item.get('sku', item_name)
                units = item.get('units', 1)
                price = float(item.get('item_price', 0))
                
                # 簡易マッピング（商品名ベース）
                common_code = get_common_code_from_name(item_name)
                
                # 重複チェック
                existing = supabase.table('sales_master').select('id').eq('platform_order_id', order_number).eq('common_code', common_code).execute()
                
                if not existing.data:
                    # 売上データを挿入
                    sale_record = {
                        'sale_date': order_date,
                        'common_code': common_code,
                        'platform_name': 'rakuten',
                        'platform_order_id': order_number,
                        'quantity': units,
                        'unit_price': price,
                        'total_amount': price * units,
                        'is_mapped': not common_code.startswith('UNMAPPED_')
                    }
                    
                    try:
                        supabase.table('sales_master').insert(sale_record).execute()
                        converted_count += 1
                    except Exception as e:
                        print(f"挿入エラー: {str(e)}")
                        skipped_count += 1
                else:
                    skipped_count += 1
        
        return {
            "status": "success",
            "message": f"楽天売上データ変換完了: {converted_count}件変換、{skipped_count}件スキップ",
            "converted_count": converted_count,
            "skipped_count": skipped_count,
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

def get_common_code_from_name(item_name: str) -> str:
    """商品名から共通コードを推定（簡易版）"""
    item_name_lower = item_name.lower()
    
    # 既知の商品パターン
    if 'ふわふわスモークサーモン' in item_name or 'ふわふわスモーク' in item_name:
        return 'CM042'  # 実際のマッピング
    elif 'スモークサーモンチップ' in item_name or 'サーモンチップ' in item_name:
        return 'CM043'
    elif 'コーンフレーク' in item_name:
        return 'C01'
    elif 'にんじんフレーク' in item_name:
        return 'C02'
    else:
        # 未マッピング商品
        return f'UNMAPPED_{item_name.replace(" ", "_")[:20]}'

@app.get("/api/check_sales_conversion")
async def check_sales_conversion():
    """売上データ変換状況の確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 注文データ数
        orders_count = supabase.table('orders').select('count').execute()
        order_items_count = supabase.table('order_items').select('count').execute()
        
        # 売上データ数（存在する場合）
        try:
            sales_count = supabase.table('sales_master').select('count').execute()
            sales_exists = True
            sales_total = len(sales_count.data) if sales_count.data else 0
        except:
            sales_exists = False
            sales_total = 0
        
        return {
            "orders_count": len(orders_count.data) if orders_count.data else 0,
            "order_items_count": len(order_items_count.data) if order_items_count.data else 0,
            "sales_master_exists": sales_exists,
            "sales_count": sales_total,
            "conversion_needed": not sales_exists or sales_total == 0,
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