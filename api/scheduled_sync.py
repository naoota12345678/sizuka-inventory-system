from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import pytz
import os
from supabase import create_client, Client
import httpx
from typing import Dict, Any

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.post("/api/scheduled_sync")
async def scheduled_sync(
    bulk_sync_days: Optional[int] = Query(None, description="過去何日分を一括同期するか")
):
    """定時実行用の同期処理 - マッピング同期 → 楽天同期（午前3時実行）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        results = {
            "status": "started",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "steps": []
        }
        
        # ステップ1: スプレッドシート（マッピング）同期
        try:
            # TODO: 実際のスプレッドシート同期API呼び出し
            async with httpx.AsyncClient() as client:
                # sync-sheetsエンドポイントを呼び出し
                sheets_response = await client.post(
                    f"{os.getenv('BASE_URL', 'https://sizuka-inventory-system.vercel.app')}/sync-sheets",
                    timeout=300  # 5分タイムアウト
                )
                
                if sheets_response.status_code == 200:
                    sheets_data = sheets_response.json()
                    results["steps"].append({
                        "step": "mapping_sync",
                        "status": "success",
                        "message": "マッピング同期完了",
                        "data": sheets_data,
                        "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                    })
                else:
                    results["steps"].append({
                        "step": "mapping_sync",
                        "status": "error",
                        "message": f"HTTP {sheets_response.status_code}",
                        "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                    })
            
        except Exception as e:
            results["steps"].append({
                "step": "mapping_sync",
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            })
        
        # ステップ2: 楽天注文同期
        try:
            days_to_sync = bulk_sync_days or 1  # デフォルトは1日分
            
            async with httpx.AsyncClient() as client:
                # sync-ordersエンドポイントを呼び出し
                rakuten_response = await client.get(
                    f"{os.getenv('BASE_URL', 'https://sizuka-inventory-system.vercel.app')}/sync-orders?days={days_to_sync}",
                    timeout=600  # 10分タイムアウト
                )
                
                if rakuten_response.status_code == 200:
                    rakuten_data = rakuten_response.json()
                    results["steps"].append({
                        "step": "rakuten_sync",
                        "status": "success",
                        "message": f"楽天同期完了（{days_to_sync}日分）",
                        "data": rakuten_data,
                        "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                    })
                else:
                    results["steps"].append({
                        "step": "rakuten_sync",
                        "status": "error",
                        "message": f"HTTP {rakuten_response.status_code}",
                        "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                    })
            
        except Exception as e:
            results["steps"].append({
                "step": "rakuten_sync",
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            })
        
        # ステップ3: 在庫計算と更新
        try:
            # 在庫の再計算
            inventory_result = await recalculate_inventory()
            results["steps"].append({
                "step": "inventory_update",
                "status": "success",
                "data": inventory_result,
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            })
            
        except Exception as e:
            results["steps"].append({
                "step": "inventory_update",
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            })
        
        # 同期ログを保存
        try:
            log_entry = {
                "sync_type": "scheduled_daily",
                "status": "completed",
                "results": results,
                "created_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
            
            # sync_logsテーブルが存在する場合は保存
            supabase.table('sync_logs').insert(log_entry).execute()
            
        except:
            # ログテーブルがない場合は無視
            pass
        
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

async def recalculate_inventory() -> Dict[str, Any]:
    """在庫の再計算"""
    try:
        # 本日の売上を集計
        today = datetime.now(pytz.timezone('Asia/Tokyo')).date()
        
        # sales_dailyから本日の売上を取得
        sales_response = supabase.table('sales_daily').select('*').eq('summary_date', today.isoformat()).execute()
        
        updated_count = 0
        
        if sales_response.data:
            for sale in sales_response.data:
                product_code = sale.get('product_code')
                units_sold = sale.get('units_sold', 0)
                
                if product_code and units_sold > 0:
                    # 在庫を減算
                    inventory = supabase.table('inventory').select('*').eq('product_code', product_code).execute()
                    
                    if inventory.data:
                        current_stock = inventory.data[0].get('current_stock', 0)
                        new_stock = max(0, current_stock - units_sold)
                        
                        # 在庫更新
                        update_response = supabase.table('inventory').update({
                            'current_stock': new_stock,
                            'updated_at': datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                        }).eq('product_code', product_code).execute()
                        
                        if update_response.data:
                            updated_count += 1
        
        return {
            "updated_products": updated_count,
            "date": today.isoformat()
        }
        
    except Exception as e:
        raise e

@app.get("/api/sync_status")
async def get_sync_status():
    """同期状況の確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 最新の同期ログを取得
        logs_response = supabase.table('sync_logs').select('*').order('created_at', desc=True).limit(10).execute()
        
        # 最後の成功した同期を検索
        last_success = None
        if logs_response.data:
            for log in logs_response.data:
                if log.get('status') == 'completed':
                    last_success = log
                    break
        
        # 次回の同期予定時刻（毎日午前3時と仮定）
        now = datetime.now(pytz.timezone('Asia/Tokyo'))
        next_sync = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now.hour >= 3:
            next_sync += timedelta(days=1)
        
        return {
            "status": "success",
            "last_sync": last_success.get('created_at') if last_success else None,
            "last_sync_status": last_success.get('status') if last_success else None,
            "next_sync": next_sync.isoformat(),
            "recent_logs": logs_response.data if logs_response.data else [],
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        # sync_logsテーブルが存在しない場合
        return {
            "status": "success",
            "message": "同期ログテーブルが未作成です",
            "next_sync": "未設定",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }