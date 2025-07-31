#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天注文同期API - メインアプリケーション
リファクタリング版
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# コアモジュール
from core.config import Config
from core.database import Database, supabase

# APIモジュール
from api.rakuten_api import RakutenAPI
from api.inventory import RakutenConnector
from api.sheets_sync import SHEETS_SYNC_AVAILABLE, sync_product_master

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーションの作成
app = FastAPI(
    title=Config.APP_NAME,
    version=Config.APP_VERSION,
    description="楽天の注文データを同期し、在庫管理を行うAPI"
)

# テンプレートとスタティックファイルの設定
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# データベース初期化のインポート（エラーハンドリング付き）
try:
    from product_master.db_setup import initialize_database
    DB_SETUP_AVAILABLE = True
except Exception as e:
    DB_SETUP_AVAILABLE = False
    logger.warning(f"データベース初期化モジュールのインポートに失敗: {e}")
    # ダミー関数を定義
    def initialize_database():
        return {}

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("Starting application...")
    try:
        # 必須環境変数の検証
        Config.validate_required_env()
        
        # データベース接続テスト
        if Database.test_connection():
            logger.info("データベース接続に成功しました")
        else:
            logger.warning("データベース接続に失敗しました")
        
        # データベースの初期化チェック
        if DB_SETUP_AVAILABLE:
            existing_tables = initialize_database()
            logger.info(f"データベース初期化チェック完了: {existing_tables}")
        
        # Google Sheets同期の状態確認
        if Config.is_sheets_sync_available():
            logger.info("Google Sheets同期が利用可能です")
        else:
            logger.info("Google Sheets同期は利用できません")
            
    except Exception as e:
        logger.error(f"起動時エラー: {str(e)}")
        # エラーが発生してもアプリケーションは継続

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Webアプリのメイン画面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api", include_in_schema=False)
async def api_root():
    """APIエンドポイント一覧（JSON）"""
    return {
        "message": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "endpoints": [
            "/health",
            "/sync-orders",
            "/sync-orders-range", 
            "/check-connection",
            "/initialize-inventory/rakuten",
            "/update-sales-rakuten",
            "/sync-sheets",
            "/docs"
        ]
    }

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "supabase_connected": Database.test_connection(),
        "db_setup_available": DB_SETUP_AVAILABLE,
        "sheets_sync_available": SHEETS_SYNC_AVAILABLE,
        "config": {
            "sheets_available": Config.is_sheets_sync_available(),
            "spreadsheet_id": bool(Config.PRODUCT_MASTER_SPREADSHEET_ID)
        }
    }

@app.get("/check-connection")
async def check_connection():
    """データベース接続確認エンドポイント"""
    if not supabase:
        return {"status": "error", "message": "Supabaseクライアントが初期化されていません"}
    
    try:
        # プラットフォーム情報の取得テスト
        platform_result = supabase.table("platform").select("*").execute()
        
        # orders テーブルのカウント
        orders_count = len(supabase.table("orders").select("id").limit(1000).execute().data)
        
        # order_items テーブルのカウント
        items_count = len(supabase.table("order_items").select("id").limit(1000).execute().data)
        
        return {
            "status": "connected",
            "platform": platform_result.data,
            "orders_count": orders_count,
            "items_count": items_count
        }
    except Exception as e:
        logger.error(f"接続チェックに失敗しました: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/sync-orders")
async def sync_orders(days: int = 1):
    """指定日数分の注文データを同期"""
    try:
        rakuten_api = RakutenAPI()
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=days)

        logger.info(f"注文同期を開始: {start_date} から {end_date}")

        # 注文データの取得
        orders = rakuten_api.get_orders(start_date, end_date)
        
        if orders:
            # Supabaseへの保存
            result = rakuten_api.save_to_supabase(orders)
            
            # 新規注文の在庫処理（オプション）
            inventory_processed = 0
            try:
                rakuten_connector = RakutenConnector()
                # 保存した注文のIDを特定
                order_numbers = [order.get("orderNumber") for order in orders]
                saved_orders = supabase.table("orders").select("id").in_("order_number", order_numbers).execute()
                
                for order in saved_orders.data:
                    order_id = order.get("id")
                    if order_id:
                        rakuten_connector.process_order_inventory(order_id)
                        inventory_processed += 1
                        
            except Exception as e:
                logger.error(f"在庫処理エラー: {str(e)}")
            
            logger.info(f"{len(orders)}件の注文を同期しました")
            return {
                "status": "success",
                "message": f"{start_date} から {end_date} の注文を同期しました",
                "order_count": len(orders),
                "sync_result": result,
                "inventory_processed": inventory_processed
            }
        else:
            logger.info("指定期間の注文が見つかりませんでした")
            return {
                "status": "success",
                "message": "指定期間の注文が見つかりませんでした",
                "order_count": 0
            }

    except Exception as e:
        logger.error(f"注文同期エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sync-orders-range")
async def sync_orders_range(start_date: str, end_date: str):
    """指定期間の注文データを同期するエンドポイント"""
    try:
        rakuten_api = RakutenAPI()
        
        # 文字列をdatetimeオブジェクトに変換
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=pytz.UTC)

        logger.info(f"注文同期を開始: {start} から {end}")

        # 注文データの取得
        orders = rakuten_api.get_orders(start, end)
        
        if orders:
            result = rakuten_api.save_to_supabase(orders)
            
            # 新規注文の在庫処理（オプション）
            inventory_processed = 0
            try:
                rakuten_connector = RakutenConnector()
                # 保存した注文のIDを特定
                order_numbers = [order.get("orderNumber") for order in orders]
                saved_orders = supabase.table("orders").select("id").in_("order_number", order_numbers).execute()
                
                for order in saved_orders.data:
                    order_id = order.get("id")
                    if order_id:
                        rakuten_connector.process_order_inventory(order_id)
                        inventory_processed += 1
                        
            except Exception as e:
                logger.error(f"在庫処理エラー: {str(e)}")
            
            logger.info(f"{len(orders)}件の注文を同期しました")
            return {
                "status": "success",
                "message": f"{start_date} から {end_date} の注文を同期しました",
                "order_count": len(orders),
                "sync_result": result,
                "inventory_processed": inventory_processed
            }
        else:
            logger.info("指定期間の注文が見つかりませんでした")
            return {
                "status": "success",
                "message": "指定期間の注文が見つかりませんでした",
                "order_count": 0
            }

    except ValueError as e:
        logger.error(f"日付形式が無効です: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail="日付形式が無効です。YYYY-MM-DD形式を使用してください。"
        )
    except Exception as e:
        logger.error(f"注文同期エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/initialize-inventory/rakuten")
async def initialize_inventory_rakuten(initial_stock: int = 0):
    """
    楽天の商品データを在庫テーブルに初期化する
    """
    try:
        connector = RakutenConnector()
        items_data = connector.extract_inventory_items()
        inventory_items = items_data.get("inventory_items", [])
        
        if not inventory_items:
            return {"message": "楽天から登録可能な商品がありません"}
        
        # 既存の在庫データを取得
        existing_inventory = supabase.table("inventory").select("product_code", "platform_id").eq(
            "platform_id", connector.initialize()
        ).execute()
        
        existing_keys = {(item["product_code"], item["platform_id"]) for item in existing_inventory.data}
        
        # 新規登録する商品データを準備
        new_inventory_items = []
        for item in inventory_items:
            if (item["product_code"], item["platform_id"]) not in existing_keys:
                new_inventory_items.append({
                    "product_code": item["product_code"],
                    "product_name": item["product_name"],
                    "platform_id": item["platform_id"],
                    "platform_product_id": item.get("platform_product_id", ""),
                    "merchant_item_id": item.get("merchant_item_id", ""),
                    "item_number": item.get("item_number", ""),
                    "variant_id": item.get("variant_id", ""),
                    "current_stock": initial_stock,
                    "minimum_stock": 0,
                    "is_active": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })
        
        # バッチ処理で登録
        batch_size = 100
        
        for i in range(0, len(new_inventory_items), batch_size):
            batch = new_inventory_items[i:i+batch_size]
            if batch:
                supabase.table("inventory").insert(batch).execute()
        
        return {
            "message": f"{len(new_inventory_items)}件の商品を在庫テーブルに登録しました",
            "platform": "rakuten",
            "existing_items": len(existing_keys),
            "new_items": len(new_inventory_items),
            "total_items": len(inventory_items)
        }
        
    except Exception as e:
        logger.error(f"在庫初期化エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-order-inventory/{order_id}")
async def process_order_inventory_endpoint(order_id: int):
    """注文の在庫処理を行うエンドポイント"""
    try:
        connector = RakutenConnector()
        result = connector.process_order_inventory(order_id)
        return result
    except Exception as e:
        logger.error(f"注文処理エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-sales-rakuten")
async def update_sales_rakuten(days: int = 7):
    """
    指定日数分の注文データから売上情報を集計・更新する
    """
    try:
        connector = RakutenConnector()
        result = connector.update_sales_data(days)
        return result
    except Exception as e:
        logger.error(f"売上更新エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/inventory-dashboard")
async def inventory_dashboard(low_stock_threshold: int = 5):
    """
    在庫状況ダッシュボードのデータを提供
    """
    try:
        # 在庫データを取得
        inventory_result = supabase.table("inventory").select("*").execute()
        
        if not inventory_result.data:
            return {"message": "在庫データがありません"}
        
        # プラットフォーム情報を取得
        platform_result = supabase.table("platform").select("id", "platform_code", "name").execute()
        platform_map = {p["id"]: {"code": p.get("platform_code", ""), "name": p["name"]} for p in platform_result.data}
        
        # 在庫状況を分析
        total_products = len(inventory_result.data)
        active_products = sum(1 for item in inventory_result.data if item["is_active"])
        
        # 在庫切れ商品
        out_of_stock = [
            {**item, "platform": platform_map.get(item["platform_id"], {"name": "不明"})}
            for item in inventory_result.data 
            if item["current_stock"] <= 0 and item["is_active"]
        ]
        
        # 在庫が少ない商品
        low_stock = [
            {**item, "platform": platform_map.get(item["platform_id"], {"name": "不明"})}
            for item in inventory_result.data 
            if 0 < item["current_stock"] <= low_stock_threshold and item["is_active"]
        ]
        
        # 商品コードプレフィックスごとの集計
        prefix_summary = {}
        for item in inventory_result.data:
            code = item["product_code"]
            # 商品コードの最初の1〜3文字をプレフィックスとして使用
            prefix = code[:1] if len(code) >= 1 else ""
            if len(code) >= 3 and code[:1].isalpha() and code[1:3].isdigit():
                prefix = code[:3]
            
            if prefix not in prefix_summary:
                prefix_summary[prefix] = {
                    "count": 0,
                    "total_stock": 0,
                    "out_of_stock": 0,
                    "low_stock": 0
                }
            
            prefix_summary[prefix]["count"] += 1
            prefix_summary[prefix]["total_stock"] += item["current_stock"]
            
            if item["current_stock"] <= 0:
                prefix_summary[prefix]["out_of_stock"] += 1
            elif item["current_stock"] <= low_stock_threshold:
                prefix_summary[prefix]["low_stock"] += 1
        
        return {
            "summary": {
                "total_products": total_products,
                "active_products": active_products,
                "out_of_stock_count": len(out_of_stock),
                "low_stock_count": len(low_stock),
                "low_stock_threshold": low_stock_threshold
            },
            "out_of_stock": out_of_stock[:10],  # 最初の10件のみ
            "low_stock": low_stock[:10],  # 最初の10件のみ
            "prefix_summary": prefix_summary
        }
        
    except Exception as e:
        logger.error(f"ダッシュボードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync-sheets")
async def sync_sheets_endpoint():
    """Google Sheetsから商品マスターデータを同期"""
    try:
        result = sync_product_master()
        
        if result["status"] == "unavailable":
            return {
                "status": "warning",
                "message": "Google Sheets同期機能は利用できません",
                "details": "必要な依存関係がインストールされていないか、認証情報が設定されていません"
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Sheets同期エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug-env")
async def debug_environment():
    """環境変数とファイルの存在を確認（デバッグ用）"""
    import os
    
    google_creds_path = Config.get_google_creds_path()
    
    result = {
        "google_creds_env": Config.GOOGLE_CREDENTIALS_FILE or "Not set",
        "google_app_creds_env": Config.GOOGLE_APPLICATION_CREDENTIALS or "Not set",
        "creds_file_found": google_creds_path is not None,
        "creds_file_path": google_creds_path,
        "working_directory": os.getcwd(),
        "sheets_sync_available": SHEETS_SYNC_AVAILABLE,
        "spreadsheet_id_set": bool(Config.PRODUCT_MASTER_SPREADSHEET_ID)
    }
    
    # 認証ファイルが存在する場合、ファイルサイズも確認
    if google_creds_path:
        result["file_size"] = os.path.getsize(google_creds_path)
    
    # 追加のデバッグ情報
    result["debug_info"] = {
        "google_auth_imported": "google.auth" in sys.modules,
        "googleapiclient_imported": "googleapiclient" in sys.modules,
        "pandas_imported": "pandas" in sys.modules,
        "sheets_config_available": Config.is_sheets_sync_available()
    }
    
    return result

# アプリケーションの起動
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True
    )