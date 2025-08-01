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

@app.get("/api/create_new_tables")
async def create_new_tables():
    """正しいテーブル構造を作成"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "operations": []
        }
        
        # SQLファイルの内容を実行（実際にはSupabaseのSQLエディタで実行する必要がある）
        sql_operations = [
            "product_mapping_master テーブル作成",
            "platform_product_mapping テーブル作成", 
            "product_bundle_components テーブル作成",
            "inventory_master テーブル作成",
            "sales_master テーブル作成",
            "インデックス作成",
            "サンプルデータ挿入"
        ]
        
        # 注意: Supabase Python clientでは直接DDL実行できないため、
        # 実際のテーブル作成はSupabaseダッシュボードのSQLエディタで実行する必要がある
        
        results["operations"] = [
            {
                "operation": op,
                "status": "manual_execution_required",
                "message": "SupabaseダッシュボードのSQLエディタで実行してください"
            }
            for op in sql_operations
        ]
        
        results["sql_file_location"] = "sql/correct_product_tables.sql"
        results["instruction"] = "Supabaseダッシュボード > SQL Editor で correct_product_tables.sql の内容を実行してください"
        
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

@app.get("/api/migrate_existing_data")
async def migrate_existing_data():
    """既存データを新しいテーブル構造に移行"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "migration_results": {}
        }
        
        # 1. 既存の在庫データを新しいinventory_masterに移行
        inventory_migration = await migrate_inventory_data()
        results["migration_results"]["inventory"] = inventory_migration
        
        # 2. 既存の注文データをsales_masterに移行
        sales_migration = await migrate_sales_data()
        results["migration_results"]["sales"] = sales_migration
        
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

async def migrate_inventory_data():
    """在庫データの移行"""
    try:
        # 既存のinventoryテーブルからデータを取得
        existing_inventory = supabase.table('inventory').select('*').execute()
        
        if not existing_inventory.data:
            return {
                "status": "warning",
                "message": "移行する在庫データがありません"
            }
        
        # 新しいテーブル形式に変換
        migrated_records = []
        for item in existing_inventory.data:
            # common_codeがない場合は、商品名ベースでマッピング
            common_code = item.get('common_code')
            if not common_code:
                # 457326558401 -> CM042 のようなマッピングを探す
                product_name = item.get('product_name', '')
                if 'ふわふわスモークサーモン' in product_name:
                    common_code = 'CM042'
                elif 'スモークサーモンチップ' in product_name:
                    common_code = 'CM043'
                else:
                    # 不明な商品の場合はスキップまたは手動確認が必要
                    continue
            
            migrated_record = {
                'common_code': common_code,
                'current_stock': item.get('current_stock', 0),
                'initial_stock': item.get('initial_stock', 0),
                'minimum_stock': item.get('minimum_stock', 5),
                'reorder_point': item.get('reorder_point', 10),
                'reference_date': item.get('reference_date', '2025-02-10')  # 基準日
            }
            migrated_records.append(migrated_record)
        
        if migrated_records:
            # 新しいテーブルに挿入（重複チェックあり）
            result = supabase.table('inventory_master').upsert(migrated_records).execute()
            return {
                "status": "success",
                "migrated_count": len(migrated_records),
                "message": f"{len(migrated_records)}件の在庫データを移行しました"
            }
        else:
            return {
                "status": "warning",
                "message": "マッピング可能なデータがありませんでした"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"在庫データ移行エラー: {str(e)}"
        }

async def migrate_sales_data():
    """売上データの移行"""
    try:
        # 既存のordersとorder_itemsテーブルからデータを取得
        existing_orders = supabase.table('orders').select('*').execute()
        existing_order_items = supabase.table('order_items').select('*').execute()
        
        if not existing_orders.data or not existing_order_items.data:
            return {
                "status": "warning",
                "message": "移行する売上データがありません"
            }
        
        # 注文と商品を結合してsales_masterに移行
        migrated_sales = []
        orders_dict = {order['id']: order for order in existing_orders.data}
        
        for item in existing_order_items.data:
            order_id = item.get('order_id')
            order = orders_dict.get(order_id)
            
            if not order:
                continue
                
            # 商品名から共通コードを推定
            product_name = item.get('item_name', '')
            common_code = None
            
            if 'ふわふわスモークサーモン' in product_name:
                common_code = 'CM042'
            elif 'スモークサーモンチップ' in product_name:
                common_code = 'CM043'
                
            if common_code:
                migrated_sale = {
                    'sale_date': order.get('order_datetime', order.get('created_at'))[:10],  # 日付のみ
                    'common_code': common_code,
                    'platform_name': 'rakuten',
                    'platform_order_id': order.get('order_number'),
                    'quantity': item.get('units', 1),
                    'unit_price': float(item.get('item_price', 0)),
                    'total_amount': float(item.get('item_price', 0)) * item.get('units', 1)
                }
                migrated_sales.append(migrated_sale)
        
        if migrated_sales:
            result = supabase.table('sales_master').insert(migrated_sales).execute()
            return {
                "status": "success",
                "migrated_count": len(migrated_sales),
                "message": f"{len(migrated_sales)}件の売上データを移行しました"
            }
        else:
            return {
                "status": "warning",
                "message": "マッピング可能な売上データがありませんでした"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"売上データ移行エラー: {str(e)}"
        }

@app.get("/api/check_migration_status")
async def check_migration_status():
    """移行状況の確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        status = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "tables": {}
        }
        
        # 新しいテーブルの存在とデータ数を確認
        new_tables = [
            'product_mapping_master',
            'platform_product_mapping', 
            'product_bundle_components',
            'inventory_master',
            'sales_master'
        ]
        
        for table_name in new_tables:
            try:
                result = supabase.table(table_name).select('count').execute()
                status["tables"][table_name] = {
                    "exists": True,
                    "record_count": len(result.data) if result.data else 0,
                    "status": "ready"
                }
            except Exception as e:
                status["tables"][table_name] = {
                    "exists": False,
                    "error": str(e),
                    "status": "needs_creation"
                }
        
        return status
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )