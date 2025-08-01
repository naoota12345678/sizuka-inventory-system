from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import pytz
import os
import asyncio
from supabase import create_client, Client
import requests

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/api/daily_sync_all")
async def daily_sync_all():
    """完全自動化：毎日午前3時実行の全同期処理"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        sync_results = {
            "sync_date": datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat(),
            "sync_time": datetime.now(pytz.timezone('Asia/Tokyo')).time().isoformat(),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "sync_steps": []
        }
        
        # ステップ1: スプレッドシートマッピング同期
        step1_result = await sync_spreadsheet_mappings()
        sync_results["sync_steps"].append({
            "step": 1,
            "name": "スプレッドシートマッピング同期",
            "result": step1_result,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        })
        
        # ステップ2: 楽天売上データ同期
        step2_result = await sync_rakuten_sales()
        sync_results["sync_steps"].append({
            "step": 2,
            "name": "楽天売上データ同期",
            "result": step2_result,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        })
        
        # ステップ3: Amazon売上データ同期（準備中）
        step3_result = await sync_amazon_sales()
        sync_results["sync_steps"].append({
            "step": 3,
            "name": "Amazon売上データ同期",
            "result": step3_result,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        })
        
        # ステップ4: ColorME売上データ同期（準備中）
        step4_result = await sync_colorme_sales()
        sync_results["sync_steps"].append({
            "step": 4,
            "name": "ColorME売上データ同期",
            "result": step4_result,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        })
        
        # ステップ5: 在庫計算更新
        step5_result = await update_inventory_calculations()
        sync_results["sync_steps"].append({
            "step": 5,
            "name": "在庫計算更新",
            "result": step5_result,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        })
        
        # ステップ6: 同期ログ保存
        await save_sync_log(sync_results)
        
        # 全体のサマリー
        success_count = sum(1 for step in sync_results["sync_steps"] if step["result"].get("status") == "success")
        total_steps = len(sync_results["sync_steps"])
        
        sync_results["summary"] = {
            "total_steps": total_steps,
            "successful_steps": success_count,
            "failed_steps": total_steps - success_count,
            "overall_status": "success" if success_count == total_steps else "partial_success"
        }
        
        return sync_results
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": f"全体同期エラー: {str(e)}",
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

async def sync_spreadsheet_mappings():
    """スプレッドシートマッピング同期"""
    try:
        # 内部API呼び出し
        base_url = os.getenv("VERCEL_URL", "https://sizuka-inventory-system.vercel.app")
        response = requests.get(f"{base_url}/api/sync_spreadsheet_mappings", timeout=60)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "message": f"スプレッドシート同期API呼び出しエラー: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"スプレッドシート同期エラー: {str(e)}"
        }

async def sync_rakuten_sales():
    """楽天売上データ同期"""
    try:
        # 昨日のデータを同期（前日分の売上を取得）
        yesterday = (datetime.now(pytz.timezone('Asia/Tokyo')).date() - timedelta(days=1)).isoformat()
        
        # 楽天注文データから売上データを生成
        orders = supabase.table('orders').select('*').gte('order_datetime', yesterday).lt('order_datetime', yesterday + 'T23:59:59').execute()
        
        if not orders.data:
            return {
                "status": "success",
                "message": f"{yesterday}の楽天注文データはありません",
                "processed_count": 0
            }
        
        processed_count = 0
        for order in orders.data:
            order_items = supabase.table('order_items').select('*').eq('order_id', order['id']).execute()
            
            if order_items.data:
                for item in order_items.data:
                    sku = item.get('sku') or item.get('item_name', '')
                    
                    # マッピング確認
                    mapping = supabase.table('platform_product_mapping').select('common_code').eq('platform_name', 'rakuten').eq('platform_product_code', sku).execute()
                    
                    common_code = mapping.data[0]['common_code'] if mapping.data else f'UNMAPPED_{sku}'
                    
                    # 重複チェック
                    existing = supabase.table('sales_master').select('id').eq('platform_order_id', order.get('order_number')).eq('common_code', common_code).execute()
                    
                    if not existing.data:
                        sale_record = {
                            'sale_date': order.get('order_datetime', '')[:10],
                            'common_code': common_code,
                            'platform_name': 'rakuten',
                            'platform_order_id': order.get('order_number'),
                            'quantity': item.get('units', 1),
                            'unit_price': float(item.get('item_price', 0)),
                            'total_amount': float(item.get('item_price', 0)) * item.get('units', 1),
                            'is_mapped': mapping.data is not None
                        }
                        
                        supabase.table('sales_master').insert(sale_record).execute()
                        processed_count += 1
        
        return {
            "status": "success",
            "message": f"楽天売上同期完了: {processed_count}件処理",
            "processed_count": processed_count,
            "sync_date": yesterday
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"楽天売上同期エラー: {str(e)}"
        }

async def sync_amazon_sales():
    """Amazon売上データ同期（準備中）"""
    try:
        # 将来実装: Amazon APIとの連携
        return {
            "status": "pending",
            "message": "Amazon売上同期は準備中です",
            "processed_count": 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Amazon売上同期エラー: {str(e)}"
        }

async def sync_colorme_sales():
    """ColorME売上データ同期（準備中）"""
    try:
        # 将来実装: ColorME APIとの連携
        return {
            "status": "pending",
            "message": "ColorME売上同期は準備中です",
            "processed_count": 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"ColorME売上同期エラー: {str(e)}"
        }

async def update_inventory_calculations():
    """在庫計算の更新"""
    try:
        today = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        
        # 内部API呼び出しで在庫計算実行
        base_url = os.getenv("VERCEL_URL", "https://sizuka-inventory-system.vercel.app")
        response = requests.get(f"{base_url}/api/current_inventory_status", timeout=60)
        
        if response.status_code == 200:
            inventory_data = response.json()
            
            # inventory_masterテーブルの current_stock を更新
            if inventory_data.get("inventory_status", {}).get("results", {}).get("products"):
                update_count = 0
                for common_code, product_data in inventory_data["inventory_status"]["results"]["products"].items():
                    calculated_stock = product_data.get("calculated_current_stock", 0)
                    
                    # current_stockを更新
                    supabase.table('inventory_master').update({
                        'current_stock': calculated_stock,
                        'updated_at': datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                    }).eq('common_code', common_code).execute()
                    
                    update_count += 1
                
                return {
                    "status": "success",
                    "message": f"在庫計算更新完了: {update_count}商品",
                    "update_count": update_count
                }
            else:
                return {
                    "status": "warning",
                    "message": "在庫計算データが取得できませんでした"
                }
        else:
            return {
                "status": "error",
                "message": f"在庫計算API呼び出しエラー: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"在庫計算更新エラー: {str(e)}"
        }

async def save_sync_log(sync_results):
    """同期ログの保存"""
    try:
        # sync_logsテーブルに保存（テーブルがない場合は作成）
        log_record = {
            'sync_date': sync_results["sync_date"],
            'sync_time': sync_results["sync_time"],
            'overall_status': sync_results["summary"]["overall_status"],
            'successful_steps': sync_results["summary"]["successful_steps"],
            'failed_steps': sync_results["summary"]["failed_steps"],
            'sync_details': sync_results["sync_steps"],
            'created_at': sync_results["timestamp"]
        }
        
        try:
            supabase.table('sync_logs').insert(log_record).execute()
        except:
            # テーブルが存在しない場合はスキップ
            pass
            
    except Exception as e:
        print(f"同期ログ保存エラー: {str(e)}")

@app.get("/api/sync_status")
async def sync_status():
    """最新の同期状況を確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 最新の同期ログを取得
        latest_sync = supabase.table('sync_logs').select('*').order('created_at', desc=True).limit(1).execute()
        
        # 今日の同期予定時刻
        today = datetime.now(pytz.timezone('Asia/Tokyo')).date()
        next_sync_time = datetime.combine(today + timedelta(days=1), datetime.min.time().replace(hour=3))
        next_sync_time = pytz.timezone('Asia/Tokyo').localize(next_sync_time)
        
        return {
            "current_time": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "next_sync_scheduled": next_sync_time.isoformat(),
            "latest_sync": latest_sync.data[0] if latest_sync.data else None,
            "sync_frequency": "毎日午前3時自動実行"
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

@app.get("/api/manual_sync_trigger")
async def manual_sync_trigger():
    """手動同期トリガー（テスト用）"""
    try:
        # 緊急時のみ使用する手動同期
        result = await daily_sync_all()
        
        return {
            "trigger_type": "manual",
            "note": "通常は午前3時に自動実行されます",
            "sync_result": result
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