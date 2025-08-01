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

@app.get("/api/convert_sales_data")
async def convert_sales_data():
    """既存の楽天注文データを売上データに変換（統合版）"""
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
            return {
                "status": "error",
                "message": "sales_masterテーブルが存在しません。まずデータベースに以下のSQLを実行してください：",
                "sql": """
CREATE TABLE sales_master (
    id SERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    common_code VARCHAR(50) NOT NULL,
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
                product_name = item.get('product_name', '')
                product_code = item.get('product_code', product_name)
                quantity = item.get('quantity', 1)
                price = float(item.get('price', 0))
                
                # 簡易マッピング（商品名ベース）
                common_code = get_common_code_from_name(product_name)
                
                # 重複チェック
                existing = supabase.table('sales_master').select('id').eq('platform_order_id', order_number).eq('common_code', common_code).execute()
                
                if not existing.data:
                    # 売上データを挿入
                    sale_record = {
                        'sale_date': order_date,
                        'common_code': common_code,
                        'platform_name': 'rakuten',
                        'platform_order_id': order_number,
                        'quantity': quantity,
                        'unit_price': price,
                        'total_amount': price * quantity,
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
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

def get_common_code_from_name(product_name: str) -> str:
    """商品名から共通コードを推定（簡易版）"""
    product_name_lower = product_name.lower()
    
    # 既知の商品パターン
    if 'ふわふわスモークサーモン' in product_name or 'ふわふわスモーク' in product_name:
        return 'CM042'
    elif 'スモークサーモンチップ' in product_name or 'サーモンチップ' in product_name:
        return 'CM043'
    elif 'コーンフレーク' in product_name:
        return 'C01'
    elif 'にんじんフレーク' in product_name:
        return 'C02'
    else:
        # 未マッピング商品
        return f'UNMAPPED_{product_name.replace(" ", "_")[:20]}'