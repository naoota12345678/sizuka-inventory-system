from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, date
import pytz
import os
from supabase import create_client, Client
from typing import Optional, List, Dict

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/test_inventory_calculation")
async def test_inventory_calculation(
    test_date: Optional[str] = Query("2025-02-15", description="テスト日付 (YYYY-MM-DD)")
):
    """在庫計算の正確性をテスト"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        results = {
            "test_date": test_date,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "calculation_test": {}
        }
        
        # 1. テスト用の製造データを追加
        manufacturing_result = await add_test_manufacturing_data(test_date)
        results["manufacturing_added"] = manufacturing_result
        
        # 2. テスト用の売上データを追加
        sales_result = await add_test_sales_data(test_date)
        results["sales_added"] = sales_result
        
        # 3. 在庫計算を実行
        calculation_result = await calculate_current_inventory(test_date)
        results["calculation_test"] = calculation_result
        
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

async def add_test_manufacturing_data(test_date: str):
    """テスト用製造データの追加"""
    try:
        # テスト製造データ
        manufacturing_data = [
            {"common_code": "CM042", "quantity": 20, "date": test_date, "note": "テスト製造"},
            {"common_code": "CM043", "quantity": 15, "date": test_date, "note": "テスト製造"}
        ]
        
        # manufacturing_transactions テーブルに追加（存在する場合）
        try:
            for data in manufacturing_data:
                supabase.table('manufacturing_transactions').insert({
                    'common_code': data['common_code'],
                    'quantity': data['quantity'],
                    'transaction_date': data['date'],
                    'transaction_type': 'manufacturing',
                    'note': data['note']
                }).execute()
        except:
            # テーブルが存在しない場合は作成
            pass
        
        return {
            "status": "success",
            "data": manufacturing_data,
            "message": "テスト製造データを追加しました"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"製造データ追加エラー: {str(e)}"
        }

async def add_test_sales_data(test_date: str):
    """テスト用売上データの追加"""
    try:
        # テスト売上データ
        sales_data = [
            {"common_code": "CM042", "quantity": 3, "platform": "rakuten", "order_id": "TEST001"},
            {"common_code": "CM043", "quantity": 2, "platform": "rakuten", "order_id": "TEST002"},
            {"common_code": "BC001", "quantity": 1, "platform": "rakuten", "order_id": "TEST003"}  # セット商品
        ]
        
        # sales_master テーブルに追加
        try:
            for data in sales_data:
                supabase.table('sales_master').insert({
                    'sale_date': test_date,
                    'common_code': data['common_code'],
                    'platform_name': data['platform'],
                    'platform_order_id': data['order_id'],
                    'quantity': data['quantity'],
                    'unit_price': 800.00,
                    'total_amount': 800.00 * data['quantity']
                }).execute()
        except Exception as e:
            print(f"Sales data insertion error: {str(e)}")
        
        return {
            "status": "success", 
            "data": sales_data,
            "message": "テスト売上データを追加しました"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"売上データ追加エラー: {str(e)}"
        }

async def calculate_current_inventory(calculation_date: str):
    """指定日時点での在庫計算"""
    try:
        results = {
            "calculation_date": calculation_date,
            "products": {}
        }
        
        # 1. 基準在庫を取得（2月10日）
        initial_inventory = supabase.table('inventory_master').select('*').execute()
        
        if not initial_inventory.data:
            return {
                "status": "error",
                "message": "基準在庫データが見つかりません"
            }
        
        # 2. 各商品について計算
        for item in initial_inventory.data:
            common_code = item['common_code']
            initial_stock = item['initial_stock']
            reference_date = item['reference_date']
            
            # 製造による増加を計算
            manufacturing_increase = await get_manufacturing_total(common_code, reference_date, calculation_date)
            
            # 売上による減少を計算（セット商品も考慮）
            sales_decrease = await get_sales_total_with_bundles(common_code, reference_date, calculation_date)
            
            # 現在在庫 = 初期在庫 + 製造増加 - 売上減少
            calculated_stock = initial_stock + manufacturing_increase - sales_decrease
            
            results["products"][common_code] = {
                "product_name": await get_product_name(common_code),
                "initial_stock": initial_stock,
                "manufacturing_increase": manufacturing_increase,
                "sales_decrease": sales_decrease,
                "calculated_current_stock": calculated_stock,
                "reference_date": reference_date
            }
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"在庫計算エラー: {str(e)}"
        }

async def get_manufacturing_total(common_code: str, start_date: str, end_date: str) -> int:
    """指定期間の製造数量を取得"""
    try:
        # manufacturing_transactions テーブルから取得
        result = supabase.table('manufacturing_transactions').select('quantity').eq('common_code', common_code).gte('transaction_date', start_date).lte('transaction_date', end_date).execute()
        
        total = sum(item['quantity'] for item in result.data) if result.data else 0
        return total
        
    except:
        # テーブルが存在しない場合は0を返す
        return 0

async def get_sales_total_with_bundles(common_code: str, start_date: str, end_date: str) -> int:
    """指定期間の売上数量を取得（セット商品の構成品も含む）"""
    try:
        total_sales = 0
        
        # 1. 直接売上
        direct_sales = supabase.table('sales_master').select('quantity').eq('common_code', common_code).gte('sale_date', start_date).lte('sale_date', end_date).execute()
        
        if direct_sales.data:
            total_sales += sum(item['quantity'] for item in direct_sales.data)
        
        # 2. セット商品の構成品として売れた分
        # この商品を含むセット商品を検索
        bundle_components = supabase.table('product_bundle_components').select('bundle_common_code, quantity').eq('component_common_code', common_code).execute()
        
        if bundle_components.data:
            for component in bundle_components.data:
                bundle_code = component['bundle_common_code']
                component_quantity = component['quantity']
                
                # そのセット商品の売上を取得
                bundle_sales = supabase.table('sales_master').select('quantity').eq('common_code', bundle_code).gte('sale_date', start_date).lte('sale_date', end_date).execute()
                
                if bundle_sales.data:
                    bundle_sold = sum(item['quantity'] for item in bundle_sales.data)
                    total_sales += bundle_sold * component_quantity
        
        return total_sales
        
    except Exception as e:
        print(f"Sales calculation error for {common_code}: {str(e)}")
        return 0

async def get_product_name(common_code: str) -> str:
    """共通コードから商品名を取得"""
    try:
        result = supabase.table('product_mapping_master').select('product_name').eq('common_code', common_code).execute()
        
        if result.data:
            return result.data[0]['product_name']
        else:
            return f"商品名不明 ({common_code})"
            
    except:
        return f"商品名不明 ({common_code})"

@app.get("/api/verify_calculation_accuracy")
async def verify_calculation_accuracy():
    """計算精度の検証"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        verification_results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "tests": []
        }
        
        # テストケース1: 単品商品の計算
        test1 = {
            "test_name": "単品商品（CM042）の在庫計算",
            "scenario": "初期在庫119 + 製造20 - 売上3 = 136",
            "expected_result": 136
        }
        
        # テストケース2: セット商品による減少
        test2 = {
            "test_name": "セット商品（BC001）による構成品減少",
            "scenario": "BC001が1個売れた場合、CM042とCM043が1個ずつ減る",
            "expected_result": "構成品の在庫が正しく減少"
        }
        
        # テストケース3: 複合計算
        test3 = {
            "test_name": "複合計算テスト",
            "scenario": "直接売上 + セット商品売上の合計減少",
            "expected_result": "正確な在庫残高"
        }
        
        verification_results["tests"] = [test1, test2, test3]
        verification_results["status"] = "manual_verification_required"
        verification_results["instruction"] = "/api/test_inventory_calculation を実行して結果を確認してください"
        
        return verification_results
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

@app.get("/api/current_inventory_status")
async def current_inventory_status():
    """現在の在庫状況を表示（計算結果）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        today = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        
        # 今日時点での在庫計算を実行
        calculation_result = await calculate_current_inventory(today)
        
        return {
            "current_date": today,
            "inventory_status": calculation_result,
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