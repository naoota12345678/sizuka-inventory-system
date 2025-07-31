#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天注文同期API - 完全統合版
Complete Sales Analytics System
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

# 🔥 新機能: 完全統合システム
from complete_integration import integrate_complete_system

# 🔥 シンプルダッシュボードAPI（フォールバック用）
from simple_dashboard_api import SimpleDashboardAPI, add_simple_dashboard_endpoints

# 🔥 楽天在庫連動システム
from rakuten_inventory_integration import RakutenInventoryIntegration, add_inventory_integration_endpoints

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーションの作成
app = FastAPI(
    title="楽天注文同期 & 完全売上分析システム",
    version="3.0 - Complete Edition",
    description="楽天の注文データを同期し、包括的な売上分析を提供するAPI"
)

# テンプレートとスタティックファイルの設定
templates = Jinja2Templates(directory="templates")
# staticディレクトリが存在する場合のみマウント
import os
if os.path.exists("static"):
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
    logger.info("Starting Complete Sales Analytics System...")
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
        
        # 🔥 完全統合システムの起動
        integration_success = integrate_complete_system(app)
        if integration_success:
            logger.info("✅ 完全売上分析システムが正常に統合されました")
            logger.info("利用可能な機能:")
            logger.info("- 売上ダッシュボード")
            logger.info("- 期間別分析")
            logger.info("- 在庫管理")
            logger.info("- アラートシステム")
            logger.info("- 商品パフォーマンス分析")
        else:
            logger.error("❌ 完全統合システムの起動に失敗しました")
        
        # 🔥 シンプルダッシュボードAPIの追加（常に利用可能）
        try:
            simple_api = SimpleDashboardAPI()
            add_simple_dashboard_endpoints(app, simple_api)
            logger.info("✅ シンプルダッシュボードAPIが統合されました")
            logger.info("利用可能なエンドポイント:")
            logger.info("- /simple-dashboard/summary - 売上サマリー")
            logger.info("- /simple-dashboard/test - 接続テスト")
        except Exception as e:
            logger.error(f"❌ シンプルダッシュボードAPIの統合に失敗: {str(e)}")
        
        # 🔥 楽天在庫連動システムの追加
        try:
            inventory_integration = RakutenInventoryIntegration()
            add_inventory_integration_endpoints(app, inventory_integration)
            logger.info("✅ 楽天在庫連動システムが統合されました")
            logger.info("利用可能な在庫機能:")
            logger.info("- /inventory/status - 在庫状況確認")
            logger.info("- /inventory/initialize-from-master - 在庫初期化")
            logger.info("- /inventory/process-order/{order_id} - 注文在庫処理")
            logger.info("- /inventory/mapping-test/{rakuten_code} - マッピングテスト")
        except Exception as e:
            logger.error(f"❌ 楽天在庫連動システムの統合に失敗: {str(e)}")
            
    except Exception as e:
        logger.error(f"起動時エラー: {str(e)}")
        # エラーが発生してもアプリケーションは継続

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Webアプリのメイン画面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "system": "Complete Sales Analytics System",
        "version": "3.0",
        "supabase_connected": Database.test_connection(),
        "db_setup_available": DB_SETUP_AVAILABLE,
        "sheets_sync_available": SHEETS_SYNC_AVAILABLE,
        "features": {
            "sales_dashboard": "✅",
            "period_analytics": "✅", 
            "inventory_management": "✅",
            "alert_system": "✅",
            "product_analysis": "✅"
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
        
        # 統合商品テーブルのチェック
        try:
            products_count = len(supabase.table("unified_products").select("id").limit(10).execute().data)
        except:
            products_count = 0
        
        # 注文テーブルのチェック
        try:
            orders_count = len(supabase.table("orders").select("id").limit(10).execute().data)
        except:
            orders_count = 0
        
        return {
            "status": "connected",
            "system": "Complete Analytics System",
            "platform": platform_result.data,
            "products_count": products_count,
            "orders_count": orders_count,
            "database_schema": "optimized"
        }
    except Exception as e:
        logger.error(f"接続チェックに失敗しました: {str(e)}")
        return {"status": "error", "message": str(e)}

# 🔥 既存の楽天同期機能（改良版）
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
            
            # 🔥 新機能: 自動分析処理
            try:
                from complete_integration import CompleteSystemIntegration
                integration = CompleteSystemIntegration()
                analytics_result = integration.analytics.process_order_analytics(orders)
                logger.info(f"分析処理完了: {analytics_result.get('status', 'unknown')}")
            except Exception as e:
                logger.warning(f"分析処理でエラー: {str(e)}")
                analytics_result = {"status": "skipped", "reason": str(e)}
            
            logger.info(f"{len(orders)}件の注文を同期しました")
            return {
                "status": "success",
                "message": f"{start_date} から {end_date} の注文を同期しました",
                "order_count": len(orders),
                "sync_result": result,
                "analytics_result": analytics_result
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
            
            # 🔥 新機能: 自動分析処理
            try:
                from complete_integration import CompleteSystemIntegration
                integration = CompleteSystemIntegration()
                analytics_result = integration.analytics.process_order_analytics(orders)
            except Exception as e:
                logger.warning(f"分析処理でエラー: {str(e)}")
                analytics_result = {"status": "skipped", "reason": str(e)}
            
            logger.info(f"{len(orders)}件の注文を同期しました")
            return {
                "status": "success",
                "message": f"{start_date} から {end_date} の注文を同期しました",
                "order_count": len(orders),
                "sync_result": result,
                "analytics_result": analytics_result
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

# 🔥 統合システム用のメイン画面
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """売上ダッシュボード画面（将来のフロントエンド用）"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>楽天売上分析ダッシュボード</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { background: #f0f8ff; padding: 20px; border-radius: 8px; }
            .feature { margin: 20px 0; padding: 15px; border-left: 4px solid #4CAF50; }
            .api-link { color: #2196F3; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 楽天売上分析ダッシュボード</h1>
            <p>Complete Sales Analytics System v3.0</p>
        </div>
        
        <div class="feature">
            <h3>📊 利用可能な分析機能</h3>
            <ul>
                <li><strong>🟢 動作確認済み:</strong></li>
                <li><a href="/simple-dashboard/summary" class="api-link">売上サマリー（シンプル版）</a></li>
                <li><a href="/simple-dashboard/test" class="api-link">データベーステスト</a></li>
                <li><a href="/system/status" class="api-link">システムステータス</a></li>
                <li><strong>🔧 高度な機能:</strong></li>
                <li><a href="/sales-dashboard/summary-stats" class="api-link">売上サマリー（高度版）</a></li>
                <li><a href="/sales-dashboard/platforms" class="api-link">プラットフォーム比較</a></li>
                <li><a href="/period-analytics/preset/last_30_days" class="api-link">過去30日の分析</a></li>
            </ul>
        </div>
        
        <div class="feature">
            <h3>🔧 API ドキュメント</h3>
            <p><a href="/docs" class="api-link">Swagger UI で全APIを確認</a></p>
        </div>
    </body>
    </html>
    """)

# アプリケーションの起動
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Complete Sales Analytics System on port {port}")
    uvicorn.run(
        "main_complete:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True
    )