from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta, date
import pytz
import os
from supabase import create_client, Client
from typing import Optional, List, Dict
import logging

app = FastAPI()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.post("/api/bulk_sync")
async def bulk_sync(
    start_date: str = Query(..., description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)、省略時は本日まで")
):
    """過去データの一括同期 - 指定期間の在庫履歴を再構築"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 日付パース
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else date.today()
        
        if start > end:
            return {"error": "開始日は終了日より前である必要があります"}
        
        results = {
            "status": "started",
            "period": f"{start} to {end}",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "days_processed": [],
            "summary": {
                "total_days": (end - start).days + 1,
                "success_days": 0,
                "failed_days": 0,
                "total_transactions": 0
            }
        }
        
        # 在庫履歴テーブルの確認/作成
        await ensure_inventory_history_table()
        
        # 初期在庫のスナップショット取得
        initial_inventory = await get_initial_inventory_snapshot(start)
        
        # 日付ごとに処理
        current_date = start
        while current_date <= end:
            try:
                day_result = await process_single_day(current_date, initial_inventory)
                
                results["days_processed"].append({
                    "date": current_date.isoformat(),
                    "status": "success",
                    "transactions": day_result["transactions"],
                    "products_affected": day_result["products_affected"]
                })
                
                results["summary"]["success_days"] += 1
                results["summary"]["total_transactions"] += day_result["transactions"]
                
            except Exception as e:
                logger.error(f"Error processing {current_date}: {str(e)}")
                results["days_processed"].append({
                    "date": current_date.isoformat(),
                    "status": "error",
                    "message": str(e)
                })
                results["summary"]["failed_days"] += 1
            
            current_date += timedelta(days=1)
        
        results["status"] = "completed"
        results["completed_at"] = datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        
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

async def ensure_inventory_history_table():
    """在庫履歴テーブルの確認/作成"""
    try:
        # inventory_historyテーブルが存在するか確認
        test_query = supabase.table('inventory_history').select('*').limit(1)
        test_query.execute()
    except:
        # テーブルが存在しない場合は作成
        logger.info("Creating inventory_history table...")
        # 注: Supabaseダッシュボードで以下のテーブルを作成する必要があります
        """
        CREATE TABLE inventory_history (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            product_code VARCHAR(20) NOT NULL,
            product_name VARCHAR(255),
            opening_stock INTEGER DEFAULT 0,
            production_qty INTEGER DEFAULT 0,
            sales_qty INTEGER DEFAULT 0,
            adjustment_qty INTEGER DEFAULT 0,
            closing_stock INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, product_code)
        );
        """
        raise Exception("inventory_historyテーブルが存在しません。Supabaseで作成してください。")

async def get_initial_inventory_snapshot(start_date: date) -> Dict[str, int]:
    """指定日の初期在庫を取得"""
    try:
        # 現在の在庫を基準とする（簡易版）
        inventory_response = supabase.table('inventory').select('product_code, current_stock').execute()
        
        snapshot = {}
        for item in inventory_response.data or []:
            snapshot[item['product_code']] = item.get('current_stock', 0)
        
        return snapshot
        
    except Exception as e:
        logger.error(f"Error getting inventory snapshot: {str(e)}")
        return {}

async def process_single_day(process_date: date, inventory_snapshot: Dict[str, int]) -> Dict:
    """1日分のデータを処理"""
    try:
        products_affected = set()
        transaction_count = 0
        
        # 1. 売上データの取得（sales_daily）
        sales_response = supabase.table('sales_daily').select('*').eq('summary_date', process_date.isoformat()).execute()
        
        daily_changes = {}  # product_code -> {sales: 0, production: 0}
        
        # 売上データの集計
        for sale in sales_response.data or []:
            product_code = sale.get('product_code')
            units_sold = sale.get('units_sold', 0)
            
            if product_code and units_sold > 0:
                if product_code not in daily_changes:
                    daily_changes[product_code] = {'sales': 0, 'production': 0}
                
                daily_changes[product_code]['sales'] += units_sold
                products_affected.add(product_code)
                transaction_count += 1
        
        # 2. 製造データの取得（もしあれば）
        # inventory_transactionsテーブルから製造データを取得
        try:
            production_response = supabase.table('inventory_transactions').select('*').eq(
                'transaction_date', process_date.isoformat()
            ).eq('transaction_type', 'production').execute()
            
            for production in production_response.data or []:
                product_code = production.get('product_code')
                quantity = production.get('quantity', 0)
                
                if product_code and quantity > 0:
                    if product_code not in daily_changes:
                        daily_changes[product_code] = {'sales': 0, 'production': 0}
                    
                    daily_changes[product_code]['production'] += quantity
                    products_affected.add(product_code)
                    transaction_count += 1
        except:
            # inventory_transactionsテーブルがない場合は無視
            pass
        
        # 3. 在庫履歴の記録
        for product_code, changes in daily_changes.items():
            opening_stock = inventory_snapshot.get(product_code, 0)
            sales_qty = changes['sales']
            production_qty = changes['production']
            closing_stock = opening_stock + production_qty - sales_qty
            
            # 在庫履歴に記録
            history_entry = {
                'date': process_date.isoformat(),
                'product_code': product_code,
                'opening_stock': opening_stock,
                'production_qty': production_qty,
                'sales_qty': sales_qty,
                'closing_stock': max(0, closing_stock),  # 負の在庫は0に
                'created_at': datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
            
            # Upsert（既存レコードがあれば更新、なければ挿入）
            supabase.table('inventory_history').upsert(history_entry).execute()
            
            # スナップショットを更新
            inventory_snapshot[product_code] = max(0, closing_stock)
        
        return {
            "transactions": transaction_count,
            "products_affected": len(products_affected)
        }
        
    except Exception as e:
        logger.error(f"Error processing day {process_date}: {str(e)}")
        raise e

@app.get("/api/inventory_history")
async def get_inventory_history(
    product_code: Optional[str] = Query(None, description="商品コード"),
    start_date: Optional[str] = Query(None, description="開始日"),
    end_date: Optional[str] = Query(None, description="終了日"),
    limit: Optional[int] = Query(100, description="取得件数")
):
    """在庫履歴の取得"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        query = supabase.table('inventory_history').select('*')
        
        if product_code:
            query = query.eq('product_code', product_code)
        
        if start_date:
            query = query.gte('date', start_date)
        
        if end_date:
            query = query.lte('date', end_date)
        
        query = query.order('date', desc=True).limit(limit)
        
        response = query.execute()
        
        return {
            "status": "success",
            "count": len(response.data) if response.data else 0,
            "items": response.data if response.data else [],
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