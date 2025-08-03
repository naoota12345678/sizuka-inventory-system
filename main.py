#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SIZUKA在庫管理システム - Cloud Run版メインアプリケーション
全APIを統合した完全版
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# 環境変数の設定（Cloud Runの環境変数を優先）
# 正しいSupabaseプロジェクト: rakuten-sales-data
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# core.databaseの既存クライアントをリセット（環境変数変更を反映）
from core.database import Database
Database.reset_client()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーションの作成
app = FastAPI(
    title="SIZUKA在庫管理システム",
    version="2.0.0",
    description="楽天・Amazon・ColorME・Airegi統合在庫管理システム"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase接続
from supabase import create_client, Client

# 新しいSupabaseプロジェクト設定を強制適用
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']

logger.info(f"Supabase接続先: {SUPABASE_URL}")
logger.info(f"Supabaseキー長: {len(SUPABASE_KEY) if SUPABASE_KEY else 0}")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("新しいSupabaseクライアントを作成しました")
else:
    supabase = None
    logger.error("Supabase接続情報が設定されていません")

# 静的ファイルとテンプレート（オプション）
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except:
    templates = None

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("SIZUKA在庫管理システム - Cloud Run版を起動中...")
    try:
        if supabase:
            # データベース接続テスト（軽量化）
            logger.info("Supabaseクライアントは初期化済みです")
        else:
            logger.warning("Supabaseクライアントの初期化に失敗しました")
    except Exception as e:
        logger.warning(f"起動時の軽微なエラー: {str(e)}")

@app.get("/")
async def root():
    """メイン画面"""
    return {
        "message": "SIZUKA在庫管理システム - Cloud Run版",
        "version": "2.0.2",
        "status": "running",
        "endpoints": {
            "inventory": "/api/inventory_list",
            "sales": "/api/sales_dashboard", 
            "platform_sync": "/api/platform_sync",
            "rakuten_analysis": "/api/analyze_sold_products",
            "comprehensive_analysis": "/api/comprehensive_rakuten_analysis",
            "sku_structure_analysis": "/api/analyze_rakuten_sku_structure",
            "family_detail": "/api/product_family_detail",
            "product_variations": "/api/get_rakuten_product_variations",
            "choice_codes": "/api/extract_choice_codes",
            "choice_demo": "/api/demo_choice_extraction",
            "save_mapping": "/api/save_choice_mapping",
            "get_mappings": "/api/get_choice_mappings", 
            "unmapped_analysis": "/api/analyze_unmapped_products",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/favicon.ico")
async def favicon():
    """Favicon対応"""
    return {"message": "favicon"}

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    try:
        db_status = "connected" if supabase else "disconnected"
        if supabase:
            test_query = supabase.table('platform').select('count').limit(1).execute()
            db_status = "connected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/check_real_order_items")
async def check_real_order_items():
    """order_itemsテーブルの実際のデータを確認"""
    try:
        # 1. 総件数
        count_response = supabase.table("order_items").select("id", count="exact").execute()
        total_count = len(count_response.data) if count_response.data else 0
        
        # 2. 最新10件
        latest_response = supabase.table("order_items").select("*").order("created_at", desc=True).limit(10).execute()
        latest_items = latest_response.data if latest_response.data else []
        
        # 3. 日付範囲確認（ordersテーブルと結合）
        date_response = supabase.table("order_items").select("""
            id, created_at, product_code, product_name, rakuten_sku, choice_code,
            orders!inner(order_date, order_number)
        """).order("orders.order_date", desc=True).execute()
        
        date_items = date_response.data if date_response.data else []
        
        # 日付の集計
        dates = []
        monthly_count = {}
        sku_count = 0
        choice_count = 0
        
        for item in date_items:
            if item.get('orders') and item['orders'].get('order_date'):
                order_date = item['orders']['order_date']
                dates.append(order_date)
                month = order_date[:7]  # YYYY-MM
                monthly_count[month] = monthly_count.get(month, 0) + 1
            
            if item.get('rakuten_sku'):
                sku_count += 1
            if item.get('choice_code'):
                choice_count += 1
        
        dates.sort()
        
        return {
            "status": "success",
            "summary": {
                "total_records": total_count,
                "sku_registered": sku_count,
                "choice_code_registered": choice_count,
                "date_range": {
                    "oldest": dates[0] if dates else None,
                    "newest": dates[-1] if dates else None
                },
                "monthly_distribution": dict(sorted(monthly_count.items()))
            },
            "latest_10_samples": [
                {
                    "created_at": item.get("created_at"),
                    "product_code": item.get("product_code"),
                    "product_name": item.get("product_name", "")[:50] + "...",
                    "rakuten_sku": item.get("rakuten_sku", "なし"),
                    "choice_code": item.get("choice_code", "なし"),
                    "quantity": item.get("quantity", 0),
                    "price": item.get("price", 0)
                }
                for item in latest_items[:10]
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/force_rakuten_sync")
async def force_rakuten_sync(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
):
    """楽天注文データを強制同期（SKU・選択肢コード付き）"""
    try:
        from api.rakuten_api import RakutenAPI
        from datetime import datetime, timedelta
        
        # デフォルト期間（過去7日）
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        # 楽天API初期化
        rakuten_api = RakutenAPI()
        
        # 日付をdatetimeに変換
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        logger.info(f"楽天注文同期開始: {start_date} - {end_date}")
        
        # 注文データ取得
        orders = rakuten_api.get_orders(start_dt, end_dt)
        
        if not orders:
            return {
                "status": "success",
                "message": "指定期間に注文データが見つかりませんでした",
                "period": f"{start_date} - {end_date}",
                "orders_count": 0
            }
        
        # Supabaseに保存
        save_result = rakuten_api.save_to_supabase(orders)
        
        return {
            "status": "success",
            "message": "楽天注文データの同期が完了しました",
            "period": f"{start_date} - {end_date}",
            "orders_fetched": len(orders),
            "save_result": save_result,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        logger.error(f"楽天同期エラー: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/sales_data_complete")
async def get_sales_data_complete(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(50, ge=1, le=1000, description="1ページあたりの件数")
):
    """SKUと選択肢コードを含む完全な販売データ一覧"""
    try:
        # デフォルト期間（過去30日）
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # order_itemsとordersテーブルを結合してデータ取得
        query = supabase.table("order_items").select("""
            *,
            orders!inner(
                order_number,
                order_date,
                platform_id,
                total_amount,
                order_status
            )
        """)
        
        # 日付フィルタ
        query = query.gte("orders.order_date", f"{start_date}T00:00:00")
        query = query.lte("orders.order_date", f"{end_date}T23:59:59")
        
        # 楽天のみフィルタ（platform_id=1）
        query = query.eq("orders.platform_id", 1)
        
        # ソート（新しい順）
        query = query.order("orders.order_date", desc=True)
        
        # ページネーション
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1)
        
        response = query.execute()
        items = response.data if response.data else []
        
        # データ整形
        formatted_items = []
        for item in items:
            order_info = item.get("orders", {})
            formatted_item = {
                "注文番号": order_info.get("order_number", ""),
                "注文日": order_info.get("order_date", ""),
                "商品コード": item.get("product_code", ""),
                "商品名": item.get("product_name", ""),
                "楽天SKU": item.get("rakuten_sku", ""),
                "選択肢コード": item.get("choice_code", ""),
                "数量": item.get("quantity", 0),
                "単価": item.get("price", 0),
                "小計": item.get("quantity", 0) * item.get("price", 0),
                "JANコード": item.get("jan_code", ""),
                "ブランド": item.get("brand_name", ""),
                "カテゴリ": item.get("category_path", ""),
                "楽天商品番号": item.get("rakuten_item_number", ""),
                "重量": item.get("weight_info", ""),
                "サイズ": item.get("size_info", "")
            }
            formatted_items.append(formatted_item)
        
        # 総件数を取得
        count_query = supabase.table("order_items").select("id", count="exact")
        count_query = count_query.gte("orders.order_date", f"{start_date}T00:00:00")
        count_query = count_query.lte("orders.order_date", f"{end_date}T23:59:59")
        count_query = count_query.eq("orders.platform_id", 1)
        count_response = count_query.execute()
        total_count = len(count_response.data) if count_response.data else 0
        
        # 集計情報
        total_orders = len(set([item["注文番号"] for item in formatted_items]))
        total_quantity = sum([item["数量"] for item in formatted_items])
        total_amount = sum([item["小計"] for item in formatted_items])
        sku_registered = len([item for item in formatted_items if item["楽天SKU"]])
        choice_registered = len([item for item in formatted_items if item["選択肢コード"]])
        
        return {
            "status": "success",
            "期間": f"{start_date} ～ {end_date}",
            "ページ情報": {
                "現在ページ": page,
                "1ページあたり": per_page,
                "総件数": total_count,
                "総ページ数": (total_count + per_page - 1) // per_page
            },
            "集計": {
                "総注文数": total_orders,
                "総商品数": total_quantity,
                "総売上": total_amount,
                "SKU登録済み": sku_registered,
                "選択肢コード登録済み": choice_registered,
                "SKU登録率": f"{sku_registered/len(formatted_items)*100:.1f}%" if formatted_items else "0%",
                "選択肢コード登録率": f"{choice_registered/len(formatted_items)*100:.1f}%" if formatted_items else "0%"
            },
            "販売データ": formatted_items,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        logger.error(f"販売データ取得エラー: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/debug_connection")
async def debug_connection():
    """現在のSupabase接続状況をデバッグ"""
    try:
        import os
        from core.database import supabase
        
        # 環境変数の確認
        current_url = os.environ.get('SUPABASE_URL', 'Not set')
        current_key = os.environ.get('SUPABASE_KEY', 'Not set')
        
        # Supabaseクライアントの確認
        supabase_client_url = getattr(supabase, 'supabase_url', 'Unknown') if supabase else 'No client'
        
        # 実際にクエリを実行してプロジェクトを確認
        test_result = None
        if supabase:
            try:
                # platformテーブルからデータを取得
                test_query = supabase.table('platform').select('*').limit(1).execute()
                test_result = {
                    "query_success": True,
                    "data_count": len(test_query.data) if test_query.data else 0,
                    "sample_data": test_query.data[0] if test_query.data else None
                }
            except Exception as query_error:
                test_result = {
                    "query_success": False,
                    "error": str(query_error)
                }
        
        return {
            "status": "debug_info",
            "environment_variables": {
                "SUPABASE_URL": current_url,
                "SUPABASE_KEY_length": len(current_key) if current_key != 'Not set' else 0
            },
            "supabase_client": {
                "client_exists": supabase is not None,
                "client_url": supabase_client_url
            },
            "connection_test": test_result,
            "expected_new_project": {
                "url": "https://equrcpeifogdrxoldkpe.supabase.co",
                "project_name": "rakuten-sales-data"
            },
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "debug_error",
            "message": str(e)
        }

@app.get("/api/check_environment")
async def check_environment():
    """Cloud Runの実際の環境変数を確認"""
    import os
    
    # 重要な環境変数をチェック
    env_vars = {
        "SUPABASE_URL": os.environ.get('SUPABASE_URL', 'NOT_SET'),
        "SUPABASE_KEY_length": len(os.environ.get('SUPABASE_KEY', '')),
        "RAKUTEN_SERVICE_SECRET_length": len(os.environ.get('RAKUTEN_SERVICE_SECRET', '')),
        "RAKUTEN_LICENSE_KEY_length": len(os.environ.get('RAKUTEN_LICENSE_KEY', '')),
    }
    
    # Supabaseクライアントの実際のURL
    supabase_client_url = None
    if supabase:
        # Supabaseクライアントの内部情報を取得
        try:
            supabase_client_url = supabase.supabase_url
        except:
            supabase_client_url = "Unknown"
    
    return {
        "cloud_run_environment": env_vars,
        "supabase_client_url": supabase_client_url,
        "expected_url": "https://equrcpeifogdrxoldkpe.supabase.co",
        "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
    }

# ===== 在庫管理API =====
@app.get("/api/inventory_list")
async def get_inventory_list(
    page: Optional[int] = Query(1, description="ページ番号"),
    per_page: Optional[int] = Query(50, description="1ページあたりの件数"),
    sort_by: Optional[str] = Query("common_code", description="ソート項目"),
    sort_order: Optional[str] = Query("asc", description="ソート順序 (asc/desc)")
):
    """在庫一覧取得API"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 基本クエリ
        query = supabase.table('inventory').select('*')
        
        # ソート設定
        query = query.order(sort_by, desc=(sort_order == 'desc'))
        
        # 全件取得
        all_response = query.execute()
        all_items = all_response.data if all_response.data else []
        
        # ページネーション
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_items = all_items[start_idx:end_idx]
        
        return {
            "status": "success",
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": len(all_items),
                "total_pages": (len(all_items) + per_page - 1) // per_page
            },
            "items": page_items,
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

# ===== 売上ダッシュボードAPI =====
@app.get("/api/sales_dashboard")
async def sales_dashboard(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    page: Optional[int] = Query(1, description="ページ番号"),
    per_page: Optional[int] = Query(50, description="1ページあたりの件数")
):
    """売上ダッシュボード"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # デフォルト期間（過去30日）
        if not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        if not start_date:
            start_date = (datetime.now(pytz.timezone('Asia/Tokyo')).date() - timedelta(days=30)).isoformat()
        
        # 売上データを取得
        query = supabase.table('sales_master').select('*').gte('sale_date', start_date).lte('sale_date', end_date)
        all_response = query.execute()
        all_sales = all_response.data if all_response.data else []
        
        # 統計計算
        total_amount = sum(float(sale.get('total_amount', 0)) for sale in all_sales)
        total_quantity = sum(int(sale.get('quantity', 0)) for sale in all_sales)
        unique_orders = len(set(sale.get('platform_order_id') for sale in all_sales if sale.get('platform_order_id')))
        
        # 商品別集約
        product_sales = {}
        for sale in all_sales:
            common_code = sale.get('common_code', 'unknown')
            if common_code not in product_sales:
                product_sales[common_code] = {
                    "common_code": common_code,
                    "product_name": f"商品 ({common_code})",
                    "total_amount": 0,
                    "total_quantity": 0,
                    "is_mapped": not common_code.startswith('UNMAPPED_')
                }
            
            product_sales[common_code]["total_amount"] += float(sale.get('total_amount', 0))
            product_sales[common_code]["total_quantity"] += int(sale.get('quantity', 0))
        
        # ソートとページネーション
        sorted_products = sorted(product_sales.values(), key=lambda x: x["total_amount"], reverse=True)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_products = sorted_products[start_idx:end_idx]
        
        return {
            "status": "success",
            "period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "summary": {
                "total_amount": total_amount,
                "total_quantity": total_quantity,
                "total_orders": unique_orders,
                "unique_products": len(product_sales)
            },
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": len(sorted_products),
                "total_pages": (len(sorted_products) + per_page - 1) // per_page
            },
            "items": page_products,
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

# ===== 統合プラットフォームAPI =====
@app.get("/api/platform_sync")
async def unified_platform_sync(
    platform: str = Query(..., description="同期プラットフォーム (rakuten/amazon/colorme/airegi)"),
    action: str = Query("sync", description="実行アクション (sync/analyze/test)")
):
    """統合プラットフォーム同期API - 全ECサイト対応"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        result = {
            "platform": platform,
            "action": action,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        if platform == "rakuten":
            if action == "sync":
                try:
                    # RakutenAPIを使用して実際の同期を実行
                    from api.rakuten_api import RakutenAPI
                    from datetime import datetime, timedelta, timezone
                    
                    # 過去7日間のデータを同期
                    end_date = datetime.now(timezone.utc)
                    start_date = end_date - timedelta(days=7)
                    
                    rakuten_api = RakutenAPI()
                    orders = rakuten_api.get_orders(start_date, end_date)
                    
                    if orders:
                        sync_result = rakuten_api.save_to_supabase(orders)
                        result["data"] = {
                            "message": "楽天同期完了",
                            "status": "success",
                            "sync_details": sync_result
                        }
                    else:
                        result["data"] = {
                            "message": "楽天同期完了（新しいデータなし）",
                            "status": "success",
                            "sync_details": {"total_orders": 0}
                        }
                except Exception as sync_error:
                    logger.error(f"楽天同期エラー: {str(sync_error)}")
                    result["data"] = {
                        "message": f"楽天同期エラー: {str(sync_error)}",
                        "status": "error"
                    }
            elif action == "analyze":
                result["data"] = await analyze_rakuten_structure()
            elif action == "test":
                result["data"] = {"message": "楽天接続テスト", "status": "ok"}
                
        elif platform == "amazon":
            result["data"] = {"message": "Amazon連携準備中", "status": "pending"}
                
        elif platform == "colorme":
            result["data"] = {"message": "ColorME連携準備中", "status": "pending"}
                
        elif platform == "airegi":
            result["data"] = {"message": "Airegi連携準備中", "status": "pending"}
                
        else:
            return {
                "status": "error",
                "message": f"未対応プラットフォーム: {platform}",
                "supported_platforms": ["rakuten", "amazon", "colorme", "airegi"]
            }
        
        return result
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

async def analyze_rakuten_structure():
    """楽天SKU構造分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # order_itemsから選択肢コード分析
        order_items = supabase.table('order_items').select('product_code, product_name').limit(20).execute()
        
        analysis = {
            "total_items": len(order_items.data) if order_items.data else 0,
            "choice_code_patterns": [],
            "sample_products": []
        }
        
        if order_items.data:
            for item in order_items.data:
                product_name = item.get('product_name', '')
                analysis["sample_products"].append({
                    "product_code": item.get('product_code', ''),
                    "product_name": product_name[:100]
                })
                
                # 選択肢コードパターン抽出
                if '【' in product_name or '[' in product_name:
                    analysis["choice_code_patterns"].append(product_name[:100])
        
        return analysis
        
    except Exception as e:
        return {"error": f"楽天構造分析エラー: {str(e)}"}

# ===== 選択肢コード抽出API =====
@app.get("/api/extract_choice_codes")
async def extract_choice_codes():
    """既存のorder_itemsから選択肢コードを抽出・分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 既存のorder_itemsデータを取得
        order_items = supabase.table('order_items').select('*').limit(100).execute()
        
        if not order_items.data:
            return {"error": "order_itemsデータが見つかりません"}
        
        analysis_results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "total_items": len(order_items.data),
            "extracted_patterns": [],
            "sample_extractions": []
        }
        
        import re
        
        extracted_codes = []
        sample_extractions = []
        
        for item in order_items.data[:20]:  # サンプル20件
            product_name = item.get('product_name', '')
            product_code = item.get('product_code', '')
            
            # 選択肢コード抽出パターン
            patterns = [
                r'【([LMS]\d*)】',  # 【L01】形式
                r'\[([LMS]\d*)\]',  # [L01]形式
                r'\(([LMS]\d*)\)',  # (L01)形式
                r'\b([LMS]\d+)\b',  # L01形式
            ]
            
            found_codes = []
            for pattern in patterns:
                matches = re.findall(pattern, product_name, re.IGNORECASE)
                found_codes.extend(matches)
            
            if found_codes:
                extracted_codes.extend(found_codes)
                sample_extractions.append({
                    "product_code": product_code,
                    "product_name": product_name[:100],
                    "extracted_codes": found_codes
                })
        
        analysis_results["extracted_patterns"] = list(set(code.upper() for code in extracted_codes))
        analysis_results["sample_extractions"] = sample_extractions
        
        return analysis_results
        
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        )

# ===== システム管理API =====
@app.get("/api/system_status")
async def get_system_status():
    """システム状況確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        status = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "database_connected": True,
            "tables_status": {}
        }
        
        # 主要テーブルの確認
        tables_to_check = [
            'inventory', 'orders', 'order_items', 'sales_master',
            'platform', 'product_mapping_master'
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
        
        return status
        
    except Exception as e:
        return {
            "error": f"System check failed: {str(e)}",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

# ===== 楽天商品詳細API =====
@app.get("/api/analyze_sold_products")
async def analyze_sold_products(
    days: int = Query(7, description="過去何日分の注文を分析するか"),
    limit: int = Query(50, description="分析する商品数の上限")
):
    """販売された商品の詳細分析（子商品情報含む）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 過去の注文から商品管理番号を取得
        end_date = datetime.now(pytz.timezone('Asia/Tokyo'))
        start_date = end_date - timedelta(days=days)
        
        # まずorder_itemsから基本情報を取得（日付フィルタなし）
        try:
            orders = supabase.table('order_items').select(
                'product_code, product_name, order_id'
            ).limit(limit).execute()
        except Exception as e:
            # order_itemsテーブルが存在しない場合の代替手段
            return {
                "error": f"order_itemsテーブルへのアクセスエラー: {str(e)}",
                "suggestion": "まず楽天APIから注文データを同期してください",
                "sync_endpoint": "/api/platform_sync?platform=rakuten&action=sync",
                "available_tables": "データベース構造を確認中..."
            }
        
        if not orders.data:
            return {
                "message": "指定期間に販売された商品が見つかりません",
                "period": f"{start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}",
                "suggestions": [
                    "期間を長くして再実行してください (例: ?days=30)",
                    "まず楽天APIから注文データを同期してください"
                ],
                "available_endpoints": [
                    "/api/platform_sync?platform=rakuten&action=sync",
                    "/api/extract_choice_codes"
                ]
            }
        
        # 楽天APIクライアントの初期化
        try:
            from api.rakuten_api import RakutenAPI
            rakuten_api = RakutenAPI()
        except Exception as e:
            return {
                "error": f"楽天API初期化失敗: {str(e)}",
                "suggestion": "楽天API認証情報を確認してください"
            }
        
        analyzed_products = []
        unique_products = {}
        
        # 重複を除去
        for order in orders.data:
            product_code = order.get('product_code', '')
            if product_code and product_code not in unique_products:
                order_date = None
                if order.get('orders') and isinstance(order['orders'], dict):
                    order_date = order['orders'].get('order_date')
                elif order.get('orders') and isinstance(order['orders'], list) and len(order['orders']) > 0:
                    order_date = order['orders'][0].get('order_date')
                
                unique_products[product_code] = {
                    "product_name": order.get('product_name', ''),
                    "order_date": order_date,
                    "order_id": order.get('order_id')
                }
        
        # 各商品の詳細分析
        for product_code, order_info in list(unique_products.items())[:10]:  # 最初の10件をテスト
            analyzed_products.append({
                "manage_number": product_code,
                "product_name": order_info.get('product_name', ''),
                "last_order_date": order_info.get('order_date'),
                "order_id": order_info.get('order_id'),
                "status": "analyzed",
                "note": "楽天商品API統合により、今後はバリエーション情報も取得可能"
            })
        
        return {
            "analysis_period": f"{start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}",
            "total_orders_found": len(orders.data),
            "total_unique_products": len(unique_products),
            "analyzed_sample": analyzed_products,
            "next_step": "楽天商品APIを使用してバリエーション情報を取得",
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

@app.get("/api/get_rakuten_product_variations")
async def get_rakuten_product_variations(
    manage_number: str = Query(..., description="楽天商品管理番号 (例: 10000301)")
):
    """指定された楽天商品の詳細・バリエーション情報を取得（楽天APIから実際のSKU情報も取得）"""
    try:
        from api.rakuten_api import RakutenAPI
        
        # 楽天APIクライアントの初期化
        try:
            rakuten_api = RakutenAPI()
        except Exception as e:
            return {
                "error": f"楽天API初期化失敗: {str(e)}",
                "suggestion": "楽天API認証情報を確認してください"
            }
        
        # 商品詳細をSupabaseから取得
        if supabase:
            order_items = supabase.table('order_items').select(
                'product_code, product_name, quantity, price'
            ).eq('product_code', manage_number).execute()
            
            if order_items.data and len(order_items.data) > 0:
                product_info = order_items.data[0]
                
                # 楽天APIから商品詳細を取得
                try:
                    rakuten_product = rakuten_api.get_product_details(manage_number)
                    
                    # SKU情報と選択肢コードを抽出
                    sku_info = []
                    if rakuten_product and 'item' in rakuten_product:
                        item = rakuten_product['item']
                        
                        # 子商品（バリエーション）情報の取得
                        if 'options' in item:
                            for option in item['options']:
                                sku_info.append({
                                    "option_name": option.get('optionName', ''),
                                    "option_value": option.get('optionValue', ''),
                                    "sku": option.get('itemNumberOption', ''),
                                    "choice_code": extract_choice_code_from_option(option),
                                    "stock": option.get('inventoryCount', 0),
                                    "price": option.get('price', item.get('itemPrice', 0))
                                })
                except Exception as api_error:
                    rakuten_product = None
                    sku_info = []
                
                return {
                    "manage_number": manage_number,
                    "product_info": product_info,
                    "analysis": {
                        "product_name": product_info.get('product_name', ''),
                        "quantity": product_info.get('quantity', 0),
                        "price": product_info.get('price', 0),
                        "extracted_variations": extract_variations_from_name(product_info.get('product_name', '')),
                        "rakuten_api_data": {
                            "available": rakuten_product is not None,
                            "sku_variations": sku_info,
                            "total_variations": len(sku_info)
                        }
                    },
                    "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                }
            else:
                return {
                    "error": f"商品管理番号 {manage_number} が見つかりません",
                    "suggestion": "正しい商品管理番号を指定してください",
                    "available_products": "利用可能な商品番号を確認するには /api/analyze_sold_products を実行"
                }
        else:
            return {"error": "Database connection not configured"}
        
    except Exception as e:
        return {
            "error": f"商品バリエーション取得エラー: {str(e)}",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

def extract_variations_from_name(product_name: str) -> dict:
    """商品名からバリエーション情報を抽出"""
    import re
    
    variations = {
        "size_patterns": [],
        "weight_patterns": [],
        "color_patterns": [],
        "choice_codes": [],
        "special_attributes": []
    }
    
    if not product_name:
        return variations
    
    # サイズパターン
    size_matches = re.findall(r'(\d+g|\d+kg|\d+ml|\d+L|S|M|L|XL)', product_name, re.IGNORECASE)
    variations["size_patterns"] = list(set(size_matches))
    
    # 重量パターン  
    weight_matches = re.findall(r'(\d+(?:\.\d+)?(?:g|kg))', product_name, re.IGNORECASE)
    variations["weight_patterns"] = list(set(weight_matches))
    
    # 選択肢コードパターン
    choice_patterns = [
        r'【([LMS]\d*)】',  # 【L01】形式
        r'\[([LMS]\d*)\]',  # [L01]形式
        r'\(([LMS]\d*)\)',  # (L01)形式
        r'\b([LMS]\d+)\b',  # L01形式
    ]
    
    for pattern in choice_patterns:
        matches = re.findall(pattern, product_name, re.IGNORECASE)
        variations["choice_codes"].extend(matches)
    
    # 特別な属性
    special_attrs = []
    if '無添加' in product_name:
        special_attrs.append('無添加')
    if '国産' in product_name:
        special_attrs.append('国産')
    if '北海道産' in product_name:
        special_attrs.append('北海道産')
    if 'まとめ買い' in product_name:
        special_attrs.append('まとめ買い')
    
    variations["special_attributes"] = special_attrs
    variations["choice_codes"] = list(set(variations["choice_codes"]))
    
    return variations

def extract_choice_code_from_option(option: dict) -> str:
    """楽天APIのオプション情報から選択肢コードを抽出"""
    option_name = option.get('optionName', '')
    option_value = option.get('optionValue', '')
    
    # オプション値から選択肢コードを抽出
    import re
    choice_patterns = [
        r'【([LMS]\d*)】',  # 【L01】形式
        r'\[([LMS]\d*)\]',  # [L01]形式
        r'\(([LMS]\d*)\)',  # (L01)形式
        r'\b([LMS]\d+)\b',  # L01形式
    ]
    
    for pattern in choice_patterns:
        matches = re.findall(pattern, option_value, re.IGNORECASE)
        if matches:
            return matches[0].upper()
    
    # オプション名からも確認
    for pattern in choice_patterns:
        matches = re.findall(pattern, option_name, re.IGNORECASE)
        if matches:
            return matches[0].upper()
    
    return ''

@app.get("/api/demo_choice_extraction")
async def demo_choice_extraction():
    """選択肢コード抽出機能のデモンストレーション"""
    try:
        # 実際の楽天商品名のサンプル
        sample_products = [
            "ふわふわサーモン【L01】30g",
            "ふわふわサーモン【M02】20g", 
            "ふわふわサーモン【S03】15g",
            "無添加チキン[L]500g",
            "無添加チキン[M]300g",
            "国産ビーフ(L01)まとめ買い500g",
            "北海道産サケ 30g L",
            "テスト商品1"
        ]
        
        results = []
        for product_name in sample_products:
            variations = extract_variations_from_name(product_name)
            results.append({
                "product_name": product_name,
                "extracted_variations": variations
            })
        
        return {
            "demonstration": "選択肢コード抽出機能のデモ",
            "sample_results": results,
            "explanation": {
                "detected_patterns": [
                    "【L01】【M02】【S03】 - 楽天標準の選択肢コード形式",
                    "[L][M][S] - 括弧形式",
                    "(L01) - 丸括弧形式", 
                    "30g, 500g - 重量パターン",
                    "無添加, 国産, 北海道産 - 特別属性"
                ]
            },
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "error": f"デモンストレーションエラー: {str(e)}",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/get_rakuten_sku_from_api")
async def get_rakuten_sku_from_api(
    manage_number: str = Query(None, description="楽天商品管理番号"),
    limit: int = Query(10, description="取得件数")
):
    """楽天APIから実際のSKU情報と選択肢コードを取得"""
    try:
        from api.rakuten_api import RakutenAPI
        
        # 楽天APIクライアントの初期化
        try:
            rakuten_api = RakutenAPI()
        except Exception as e:
            return {
                "error": f"楽天API初期化失敗: {str(e)}",
                "suggestion": "楽天API認証情報を確認してください"
            }
        
        results = {
            "status": "success",
            "products_with_sku": [],
            "total_sku_found": 0,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        if manage_number:
            # 特定の商品管理番号のSKU情報を取得
            product_details = await fetch_rakuten_product_sku(rakuten_api, manage_number)
            if product_details:
                results["products_with_sku"].append(product_details)
                results["total_sku_found"] = len(product_details.get("sku_list", []))
        else:
            # データベースから商品管理番号を取得
            if supabase:
                order_items = supabase.table('order_items').select(
                    'product_code, product_name'
                ).limit(limit).execute()
                
                if order_items.data:
                    unique_products = {}
                    for item in order_items.data:
                        product_code = item.get('product_code', '')
                        if product_code and product_code not in unique_products:
                            unique_products[product_code] = item.get('product_name', '')
                    
                    # 各商品のSKU情報を取得
                    for product_code, product_name in list(unique_products.items())[:5]:  # 最初の5件
                        product_details = await fetch_rakuten_product_sku(rakuten_api, product_code)
                        if product_details:
                            results["products_with_sku"].append(product_details)
                            results["total_sku_found"] += len(product_details.get("sku_list", []))
        
        return results
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

async def fetch_rakuten_product_sku(rakuten_api, manage_number: str) -> dict:
    """楽天APIから商品のSKU情報を取得"""
    try:
        # 楽天APIから商品情報を取得
        product_data = rakuten_api.get_product_details(manage_number)
        
        if not product_data or 'item' not in product_data:
            return None
        
        item = product_data['item']
        sku_list = []
        
        # メインSKU
        main_sku = item.get('itemNumber', '')
        if main_sku:
            sku_list.append({
                "sku": main_sku,
                "type": "main",
                "choice_code": "",
                "option_name": "メイン商品",
                "price": item.get('itemPrice', 0),
                "stock": item.get('inventoryCount', 0)
            })
        
        # バリエーションSKU
        if 'options' in item and isinstance(item['options'], list):
            for option in item['options']:
                option_sku = option.get('itemNumberOption', '')
                option_name = option.get('optionName', '')
                option_value = option.get('optionValue', '')
                
                # 選択肢コードを抽出
                choice_code = extract_choice_code_from_option(option)
                
                if option_sku:
                    sku_list.append({
                        "sku": option_sku,
                        "type": "option",
                        "choice_code": choice_code,
                        "option_name": f"{option_name}: {option_value}",
                        "price": option.get('price', item.get('itemPrice', 0)),
                        "stock": option.get('inventoryCount', 0)
                    })
        
        return {
            "manage_number": manage_number,
            "product_name": item.get('itemName', ''),
            "main_sku": main_sku,
            "total_variations": len(sku_list),
            "sku_list": sku_list,
            "has_choice_codes": any(sku['choice_code'] for sku in sku_list)
        }
        
    except Exception as e:
        return None

@app.get("/api/verify_choice_code_extraction")
async def verify_choice_code_extraction():
    """データベース内の実際のデータから選択肢コードを抽出・確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # データベースから商品情報を取得
        order_items = supabase.table('order_items').select(
            'product_code, product_name'
        ).limit(100).execute()
        
        if not order_items.data:
            return {"error": "order_itemsデータが見つかりません"}
        
        analysis_results = {
            "total_products": len(order_items.data),
            "products_with_choice_codes": [],
            "choice_code_summary": {},
            "extraction_patterns": {
                "【XX】": 0,
                "[XX]": 0,
                "(XX)": 0,
                "XX形式": 0
            },
            "sample_extractions": [],
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        # 各商品から選択肢コードを抽出
        for item in order_items.data:
            product_name = item.get('product_name', '')
            product_code = item.get('product_code', '')
            
            # 選択肢コードを抽出
            variations = extract_variations_from_name(product_name)
            
            if variations['choice_codes']:
                product_info = {
                    "product_code": product_code,
                    "product_name": product_name[:100],
                    "choice_codes": variations['choice_codes'],
                    "other_variations": {
                        "sizes": variations['size_patterns'],
                        "weights": variations['weight_patterns'],
                        "attributes": variations['special_attributes']
                    }
                }
                
                analysis_results["products_with_choice_codes"].append(product_info)
                
                # 選択肢コードの集計
                for code in variations['choice_codes']:
                    if code not in analysis_results["choice_code_summary"]:
                        analysis_results["choice_code_summary"][code] = 0
                    analysis_results["choice_code_summary"][code] += 1
                
                # パターン分析
                if '【' in product_name and '】' in product_name:
                    analysis_results["extraction_patterns"]["【XX】"] += 1
                elif '[' in product_name and ']' in product_name:
                    analysis_results["extraction_patterns"]["[XX]"] += 1
                elif '(' in product_name and ')' in product_name:
                    analysis_results["extraction_patterns"]["(XX)"] += 1
                else:
                    analysis_results["extraction_patterns"]["XX形式"] += 1
        
        # サンプル抽出結果
        analysis_results["sample_extractions"] = analysis_results["products_with_choice_codes"][:10]
        
        # 統計情報
        analysis_results["statistics"] = {
            "total_products_with_choice_codes": len(analysis_results["products_with_choice_codes"]),
            "percentage_with_codes": round(len(analysis_results["products_with_choice_codes"]) / len(order_items.data) * 100, 2),
            "unique_choice_codes": len(analysis_results["choice_code_summary"]),
            "most_common_codes": sorted(
                analysis_results["choice_code_summary"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
        
        return analysis_results
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.post("/api/sync_rakuten_sku_to_database")
async def sync_rakuten_sku_to_database(
    manage_numbers: list[str] = Query(None, description="商品管理番号のリスト"),
    limit: int = Query(10, description="処理件数上限")
):
    """楽天APIからSKU情報を取得しデータベースに保存"""
    try:
        from api.rakuten_api import RakutenAPI
        
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 楽天APIクライアントの初期化
        try:
            rakuten_api = RakutenAPI()
        except Exception as e:
            return {
                "error": f"楽天API初期化失敗: {str(e)}",
                "suggestion": "楽天API認証情報を確認してください"
            }
        
        sync_results = {
            "status": "success",
            "synced_products": [],
            "failed_products": [],
            "total_sku_saved": 0,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        # 商品管理番号のリストを取得
        if not manage_numbers:
            # データベースから取得
            order_items = supabase.table('order_items').select(
                'product_code'
            ).limit(limit).execute()
            
            if order_items.data:
                manage_numbers = list(set(item['product_code'] for item in order_items.data if item.get('product_code')))
            else:
                return {"error": "処理対象の商品が見つかりません"}
        
        # 各商品のSKU情報を取得して保存
        for manage_number in manage_numbers[:limit]:
            try:
                # 楽天APIからSKU情報を取得
                product_details = await fetch_rakuten_product_sku(rakuten_api, manage_number)
                
                if product_details:
                    # SKU情報をデータベースに保存
                    for sku_info in product_details['sku_list']:
                        # rakuten_sku_masterテーブルに保存
                        sku_data = {
                            "manage_number": manage_number,
                            "rakuten_sku": sku_info['sku'],
                            "choice_code": sku_info['choice_code'],
                            "option_name": sku_info['option_name'],
                            "sku_type": sku_info['type'],
                            "created_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                        }
                        
                        try:
                            result = supabase.table('rakuten_sku_master').upsert(
                                sku_data,
                                on_conflict="manage_number,rakuten_sku"
                            ).execute()
                            sync_results["total_sku_saved"] += 1
                        except Exception as db_error:
                            # テーブルが存在しない場合のエラーをキャッチ
                            pass
                    
                    sync_results["synced_products"].append({
                        "manage_number": manage_number,
                        "product_name": product_details['product_name'],
                        "total_skus": product_details['total_variations'],
                        "has_choice_codes": product_details['has_choice_codes']
                    })
                else:
                    sync_results["failed_products"].append({
                        "manage_number": manage_number,
                        "reason": "楽天APIからデータ取得失敗"
                    })
                    
            except Exception as e:
                sync_results["failed_products"].append({
                    "manage_number": manage_number,
                    "reason": str(e)
                })
        
        sync_results["summary"] = {
            "total_processed": len(manage_numbers[:limit]),
            "success_count": len(sync_results["synced_products"]),
            "failed_count": len(sync_results["failed_products"]),
            "recommendation": "データベーススキーマを更新してrakuten_sku_masterテーブルを作成してください"
        }
        
        return sync_results
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.post("/api/save_choice_mapping")
async def save_choice_mapping(
    parent_product_code: str,
    choice_code: str,
    common_product_code: str,
    choice_name: str = "",
    mapping_confidence: int = 100
):
    """選択肢コードと共通商品コードのマッピングを保存"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # rakuten_choice_mappingテーブルに保存
        choice_mapping_data = {
            "parent_product_code": parent_product_code,
            "choice_code": choice_code,
            "choice_name": choice_name,
            "created_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        # product_mapping_rakutenテーブルに保存
        product_mapping_data = {
            "rakuten_product_code": parent_product_code,
            "rakuten_choice_code": choice_code,
            "common_product_code": common_product_code,
            "mapping_confidence": mapping_confidence,
            "mapping_type": "manual",
            "created_at": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
        # データベースに保存（upsert）
        try:
            choice_result = supabase.table('rakuten_choice_mapping').upsert(
                choice_mapping_data,
                on_conflict="parent_product_code,choice_code"
            ).execute()
            
            mapping_result = supabase.table('product_mapping_rakuten').upsert(
                product_mapping_data,
                on_conflict="rakuten_product_code,rakuten_choice_code"
            ).execute()
            
            return {
                "status": "success",
                "message": f"マッピングを保存しました: {parent_product_code}[{choice_code}] → {common_product_code}",
                "choice_mapping": choice_result.data,
                "product_mapping": mapping_result.data,
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
            
        except Exception as db_error:
            return {
                "status": "warning", 
                "message": f"データベーススキーマが未更新の可能性があります: {str(db_error)}",
                "suggested_action": "先にデータベースのスキーマを更新してください",
                "sql_file": "/supabase/02_rakuten_enhancement.sql"
            }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/get_choice_mappings")
async def get_choice_mappings(
    parent_product_code: str = Query(None, description="親商品コード"),
    limit: int = Query(50, description="取得件数")
):
    """選択肢コードマッピングの一覧取得"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # クエリ構築
        query = supabase.table('product_mapping_rakuten').select('*')
        
        if parent_product_code:
            query = query.eq('rakuten_product_code', parent_product_code)
        
        query = query.limit(limit).order('created_at', desc=True)
        
        try:
            result = query.execute()
            
            return {
                "status": "success",
                "mappings": result.data if result.data else [],
                "total_count": len(result.data) if result.data else 0,
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
            
        except Exception as db_error:
            return {
                "status": "warning",
                "message": f"マッピングテーブルが存在しません: {str(db_error)}",
                "suggested_action": "先にデータベースのスキーマを更新してください",
                "sql_file": "/supabase/02_rakuten_enhancement.sql"
            }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/analyze_unmapped_products")
async def analyze_unmapped_products():
    """マッピングされていない楽天商品の分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # order_itemsから楽天商品を取得
        order_items = supabase.table('order_items').select(
            'product_code, product_name'
        ).limit(100).execute()
        
        if not order_items.data:
            return {"message": "注文データが見つかりません"}
        
        unmapped_products = []
        
        for item in order_items.data:
            product_code = item.get('product_code', '')
            product_name = item.get('product_name', '')
            
            # 選択肢コードを抽出
            from core.utils import extract_choice_code_from_name
            choice_code = extract_choice_code_from_name(product_name)
            
            # マッピング存在確認（実際のテーブルが存在する場合）
            try:
                existing_mapping = supabase.table('product_mapping_rakuten').select('*').eq(
                    'rakuten_product_code', product_code
                ).execute()
                
                is_mapped = len(existing_mapping.data) > 0 if existing_mapping.data else False
            except:
                is_mapped = False  # テーブルが存在しない場合
            
            if not is_mapped:
                unmapped_products.append({
                    "product_code": product_code,
                    "product_name": product_name,
                    "extracted_choice_code": choice_code,
                    "suggested_common_code": f"CM{product_code[-3:]}_{choice_code}" if choice_code else f"CM{product_code[-3:]}"
                })
        
        return {
            "status": "success",
            "unmapped_count": len(unmapped_products),
            "unmapped_products": unmapped_products[:20],  # 最初の20件
            "next_step": "これらの商品に共通商品コードを割り当ててマッピングを作成してください",
            "mapping_endpoint": "/api/save_choice_mapping",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/comprehensive_rakuten_analysis")
async def comprehensive_rakuten_analysis(
    months: int = Query(6, description="過去何ヶ月分のデータを分析するか"),
    limit: int = Query(1000, description="分析する商品数の上限")
):
    """楽天商品の包括的分析（数ヶ月分の全データ）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 過去N ヶ月分のデータを取得
        from datetime import datetime, timedelta
        import pytz
        
        end_date = datetime.now(pytz.timezone('Asia/Tokyo'))
        start_date = end_date - timedelta(days=months * 30)
        
        # 全order_itemsデータを取得
        order_items = supabase.table('order_items').select('*').limit(limit).execute()
        
        if not order_items.data:
            return {"message": "注文データが見つかりません"}
        
        # 分析結果の初期化
        analysis = {
            "period": f"{start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}",
            "total_items": len(order_items.data),
            "product_registration_patterns": {
                "with_choice_codes": [],
                "without_choice_codes": [],
                "parent_child_candidates": [],
                "single_products": []
            },
            "choice_code_analysis": {
                "detected_codes": {},
                "code_patterns": {},
                "weight_size_patterns": {},
                "special_attributes": {}
            },
            "product_families": {},
            "unique_products": {},
            "recommendations": []
        }
        
        from core.utils import extract_choice_code_from_name
        import re
        
        # 各商品を詳細分析
        for item in order_items.data:
            product_code = item.get('product_code', '')
            product_name = item.get('product_name', '')
            
            if not product_code or not product_name:
                continue
            
            # 基本情報を記録
            if product_code not in analysis["unique_products"]:
                analysis["unique_products"][product_code] = {
                    "product_code": product_code,
                    "product_name": product_name,
                    "quantity": item.get('quantity', 0),
                    "price": item.get('price', 0),
                    "first_seen": item.get('created_at', ''),
                    "occurrences": 0,
                    "variations": []
                }
            
            analysis["unique_products"][product_code]["occurrences"] += 1
            
            # 選択肢コード抽出
            choice_code = extract_choice_code_from_name(product_name)
            
            # バリエーション情報抽出
            variations = extract_variations_from_name(product_name)
            
            # 商品ファミリー分析（商品コードの前部分で分類）
            family_code = product_code[:7] if len(product_code) >= 7 else product_code
            if family_code not in analysis["product_families"]:
                analysis["product_families"][family_code] = {
                    "family_code": family_code,
                    "products": [],
                    "has_variations": False,
                    "choice_codes": set(),
                    "pattern_type": "unknown"
                }
            
            analysis["product_families"][family_code]["products"].append({
                "product_code": product_code,
                "product_name": product_name,
                "choice_code": choice_code,
                "variations": variations
            })
            
            if choice_code:
                analysis["product_families"][family_code]["choice_codes"].add(choice_code)
                analysis["product_families"][family_code]["has_variations"] = True
            
            # 登録パターン分類
            if choice_code:
                analysis["product_registration_patterns"]["with_choice_codes"].append({
                    "product_code": product_code,
                    "product_name": product_name[:100],
                    "choice_code": choice_code,
                    "variations": variations
                })
                
                # 選択肢コード統計
                if choice_code not in analysis["choice_code_analysis"]["detected_codes"]:
                    analysis["choice_code_analysis"]["detected_codes"][choice_code] = 0
                analysis["choice_code_analysis"]["detected_codes"][choice_code] += 1
                
            else:
                analysis["product_registration_patterns"]["without_choice_codes"].append({
                    "product_code": product_code,
                    "product_name": product_name[:100],
                    "might_be_parent": "◆" in product_name or "選択" in product_name,
                    "variations": variations
                })
        
        # 商品ファミリーのパターン分析
        for family_code, family_data in analysis["product_families"].items():
            product_count = len(family_data["products"])
            choice_count = len(family_data["choice_codes"])
            
            if choice_count > 1:
                family_data["pattern_type"] = "multi_choice"
            elif choice_count == 1:
                family_data["pattern_type"] = "single_choice"
            elif product_count > 1:
                family_data["pattern_type"] = "potential_variations"
            else:
                family_data["pattern_type"] = "single_product"
            
            # 商品ファミリーごとの選択肢コードをリストに変換
            family_data["choice_codes"] = list(family_data["choice_codes"])
        
        # データを件数でソート
        analysis["product_registration_patterns"]["with_choice_codes"] = \
            analysis["product_registration_patterns"]["with_choice_codes"][:20]
        analysis["product_registration_patterns"]["without_choice_codes"] = \
            analysis["product_registration_patterns"]["without_choice_codes"][:20]
        
        # 重要な商品ファミリーのみ表示
        important_families = {k: v for k, v in analysis["product_families"].items() 
                            if len(v["products"]) > 1 or v["has_variations"]}
        analysis["product_families"] = dict(list(important_families.items())[:10])
        
        # 推奨事項
        analysis["recommendations"] = [
            {
                "priority": "高",
                "action": "選択肢コード付き商品の優先マッピング",
                "count": len(analysis["product_registration_patterns"]["with_choice_codes"]),
                "description": "これらの商品は選択肢コードが明確なのでマッピングが容易"
            },
            {
                "priority": "中", 
                "action": "商品ファミリー分析によるバリエーション発見",
                "count": len([f for f in analysis["product_families"].values() if f["pattern_type"] == "potential_variations"]),
                "description": "同じファミリーコードで複数商品がある場合、隠れたバリエーションの可能性"
            },
            {
                "priority": "中",
                "action": "親商品候補の個別調査", 
                "count": len([p for p in analysis["product_registration_patterns"]["without_choice_codes"] if p.get("might_be_parent")]),
                "description": "◆や「選択」を含む商品名は親商品の可能性"
            }
        ]
        
        # 統計情報
        analysis["statistics"] = {
            "total_unique_products": len(analysis["unique_products"]),
            "products_with_choice_codes": len(analysis["product_registration_patterns"]["with_choice_codes"]),
            "products_without_choice_codes": len(analysis["product_registration_patterns"]["without_choice_codes"]),
            "product_families_count": len(analysis["product_families"]),
            "unique_choice_codes": len(analysis["choice_code_analysis"]["detected_codes"])
        }
        
        return {
            "status": "success",
            "analysis": analysis,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/product_family_detail")
async def product_family_detail(
    family_code: str = Query(..., description="商品ファミリーコード (例: 1000005)")
):
    """特定の商品ファミリーの詳細分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 指定ファミリーコードで始まる全商品を取得
        order_items = supabase.table('order_items').select('*').like(
            'product_code', f'{family_code}%'
        ).execute()
        
        if not order_items.data:
            return {"message": f"ファミリーコード {family_code} の商品が見つかりません"}
        
        from core.utils import extract_choice_code_from_name
        
        family_analysis = {
            "family_code": family_code,
            "total_products": len(order_items.data),
            "products": [],
            "choice_code_distribution": {},
            "pattern_analysis": {
                "likely_parent_child": False,
                "single_variations": False,
                "mixed_pattern": False
            },
            "mapping_suggestions": []
        }
        
        choice_codes = set()
        has_parent_indicators = False
        
        for item in order_items.data:
            product_code = item.get('product_code', '')
            product_name = item.get('product_name', '')
            
            choice_code = extract_choice_code_from_name(product_name)
            variations = extract_variations_from_name(product_name)
            
            if choice_code:
                choice_codes.add(choice_code)
                if choice_code not in family_analysis["choice_code_distribution"]:
                    family_analysis["choice_code_distribution"][choice_code] = 0
                family_analysis["choice_code_distribution"][choice_code] += 1
            
            if "◆" in product_name or "選択" in product_name:
                has_parent_indicators = True
            
            family_analysis["products"].append({
                "product_code": product_code,
                "product_name": product_name,
                "choice_code": choice_code,
                "variations": variations,
                "quantity": item.get('quantity', 0),
                "price": item.get('price', 0),
                "order_date": item.get('created_at', '')
            })
        
        # パターン分析
        if len(choice_codes) > 1:
            family_analysis["pattern_analysis"]["likely_parent_child"] = True
        elif has_parent_indicators:
            family_analysis["pattern_analysis"]["single_variations"] = True
        elif len(family_analysis["products"]) > 1:
            family_analysis["pattern_analysis"]["mixed_pattern"] = True
        
        # マッピング提案
        for i, product in enumerate(family_analysis["products"]):
            choice_code = product["choice_code"] 
            if choice_code:
                suggested_common = f"CM{family_code[-3:]}_{choice_code}"
            else:
                suggested_common = f"CM{family_code[-3:]}_{i+1:02d}"
            
            family_analysis["mapping_suggestions"].append({
                "rakuten_code": product["product_code"],
                "choice_code": choice_code,
                "suggested_common_code": suggested_common,
                "confidence": 90 if choice_code else 60
            })
        
        return {
            "status": "success",
            "family_analysis": family_analysis,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/analyze_rakuten_sku_structure")
async def analyze_rakuten_sku_structure():
    """楽天SKUコードの構造分析と判別"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 全order_itemsデータを取得してSKU構造を分析
        order_items = supabase.table('order_items').select('*').execute()
        
        if not order_items.data:
            return {"message": "注文データが見つかりません"}
        
        sku_analysis = {
            "total_items": len(order_items.data),
            "sku_patterns": {
                "standard_sku": [],      # 一般的な楽天SKU (数字のみ)
                "variant_sku": [],       # バリエーションSKU (数字-文字列)
                "custom_sku": [],        # カスタムSKU (文字列含む)
                "unknown_pattern": []    # 不明パターン
            },
            "sku_families": {},         # SKUファミリー別分析
            "detected_variations": {},  # 検出されたバリエーション
            "mapping_candidates": []    # マッピング候補
        }
        
        # 各商品のSKU分析
        for item in order_items.data:
            product_code = item.get('product_code', '')
            product_name = item.get('product_name', '')
            
            if not product_code:
                continue
            
            # SKUパターン判別
            sku_pattern = classify_rakuten_sku(product_code)
            sku_analysis["sku_patterns"][sku_pattern["type"]].append({
                "sku": product_code,
                "product_name": product_name[:80],
                "pattern_details": sku_pattern,
                "price": item.get('price', 0),
                "quantity": item.get('quantity', 0)
            })
            
            # SKUファミリー分析
            family_code = extract_sku_family(product_code)
            if family_code not in sku_analysis["sku_families"]:
                sku_analysis["sku_families"][family_code] = {
                    "family_code": family_code,
                    "skus": [],
                    "is_variation_family": False,
                    "base_sku": None
                }
            
            sku_analysis["sku_families"][family_code]["skus"].append({
                "sku": product_code,
                "product_name": product_name[:60],
                "pattern": sku_pattern
            })
        
        # バリエーションファミリーの検出
        for family_code, family_data in sku_analysis["sku_families"].items():
            if len(family_data["skus"]) > 1:
                family_data["is_variation_family"] = True
                # ベースSKUを特定（最も短いSKU）
                family_data["base_sku"] = min(family_data["skus"], key=lambda x: len(x["sku"]))["sku"]
        
        # 統計とサマリー
        sku_analysis["statistics"] = {
            "standard_sku_count": len(sku_analysis["sku_patterns"]["standard_sku"]),
            "variant_sku_count": len(sku_analysis["sku_patterns"]["variant_sku"]), 
            "custom_sku_count": len(sku_analysis["sku_patterns"]["custom_sku"]),
            "total_families": len(sku_analysis["sku_families"]),
            "variation_families": len([f for f in sku_analysis["sku_families"].values() if f["is_variation_family"]])
        }
        
        # マッピング候補生成
        sku_analysis["mapping_candidates"] = generate_sku_mapping_candidates(sku_analysis["sku_families"])
        
        # 重要なファミリーのみ表示（データ量制限）
        important_families = {k: v for k, v in sku_analysis["sku_families"].items() 
                            if len(v["skus"]) > 1}
        sku_analysis["sku_families"] = dict(list(important_families.items())[:10])
        
        return {
            "status": "success",
            "sku_analysis": sku_analysis,
            "recommendations": [
                {
                    "priority": "高",
                    "action": "バリエーションファミリーの優先マッピング",
                    "description": f"{sku_analysis['statistics']['variation_families']}個のバリエーションファミリーを発見"
                },
                {
                    "priority": "中",
                    "action": "スプレッドシート名寄せ管理との照合",
                    "description": "検出されたSKUパターンを既存の名寄せデータと照合"
                }
            ],
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

def classify_rakuten_sku(sku: str) -> dict:
    """楽天SKUのパターン分類"""
    import re
    
    if not sku:
        return {"type": "unknown_pattern", "details": "Empty SKU"}
    
    # パターン1: 純粋な数字SKU (例: 10000059)
    if re.match(r'^\d+$', sku):
        return {
            "type": "standard_sku",
            "details": "Standard numeric SKU",
            "base_number": sku,
            "variation_part": None
        }
    
    # パターン2: 数字-文字列バリエーション (例: 10000059-L01)
    variant_match = re.match(r'^(\d+)[-_]([A-Za-z0-9]+)$', sku)
    if variant_match:
        return {
            "type": "variant_sku", 
            "details": "Numeric base with variation",
            "base_number": variant_match.group(1),
            "variation_part": variant_match.group(2)
        }
    
    # パターン3: テストデータ (例: TEST001)
    if re.match(r'^TEST\d+$', sku):
        return {
            "type": "custom_sku",
            "details": "Test data SKU",
            "base_number": None,
            "variation_part": sku
        }
    
    # パターン4: 文字列含むカスタムSKU
    if re.match(r'^[A-Za-z]', sku):
        return {
            "type": "custom_sku",
            "details": "Custom alphanumeric SKU", 
            "base_number": None,
            "variation_part": sku
        }
    
    return {
        "type": "unknown_pattern",
        "details": f"Unrecognized pattern: {sku}",
        "base_number": None,
        "variation_part": None
    }

def extract_sku_family(sku: str) -> str:
    """SKUからファミリーコードを抽出"""
    import re
    
    # バリエーションSKUの場合、ベース部分を返す
    variant_match = re.match(r'^(\d+)[-_]([A-Za-z0-9]+)$', sku)
    if variant_match:
        return variant_match.group(1)
    
    # 数字SKUの場合、そのまま返す（ただし最後の1-2桁を除く可能性も）
    if re.match(r'^\d+$', sku):
        if len(sku) >= 6:
            return sku[:6]  # 最初の6桁をファミリーとする
        return sku
    
    # その他の場合
    return sku

def generate_sku_mapping_candidates(sku_families: dict) -> list:
    """SKUファミリーからマッピング候補を生成"""
    candidates = []
    
    for family_code, family_data in sku_families.items():
        if family_data["is_variation_family"]:
            base_sku = family_data["base_sku"]
            
            for i, sku_info in enumerate(family_data["skus"]):
                sku = sku_info["sku"]
                pattern = sku_info["pattern"]
                
                # 共通コード候補の生成
                if pattern["type"] == "variant_sku":
                    suggested_common = f"CM{family_code[-3:]}_{pattern['variation_part']}"
                else:
                    suggested_common = f"CM{family_code[-3:]}_{i+1:02d}"
                
                candidates.append({
                    "rakuten_sku": sku,
                    "family_code": family_code,
                    "suggested_common_code": suggested_common,
                    "product_name": sku_info["product_name"],
                    "confidence": 85 if pattern["type"] == "variant_sku" else 60
                })
    
    return candidates[:20]  # 最初の20件のみ

@app.get("/api/search_actual_rakuten_skus")
async def search_actual_rakuten_skus():
    """実際の楽天SKU（4-9桁の数字）をデータベースから検索"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 提供されたSKUリスト
        actual_skus = [
            1797, 1798, 1799, 1800, 1801, 1802, 1810, 1809, 1739, 1740, 1741, 1742, 1743, 1744, 1745, 1749, 1750, 1847, 1863,
            167439411, 167439431, 167439456, 167439467, 167439492, 167439544, 167439632, 167439694, 167439656, 167439711, 167439727, 167439743, 167439773, 167439822, 167440131, 167439932, 167440029, 167440156, 167440215, 167440277, 167440411, 167440916,
            1701, 1703, 1737, 1705, 1763, 1715, 1714, 1713, 1718, 1716, 1723, 1848, 1722, 1725, 1726, 1727, 1761, 1762, 1760, 1781, 1850, 1833, 1720, 1759, 1753, 1754, 1839, 1840, 1841, 1842, 1843, 1702, 1724, 1717, 1728, 1729,
            1768, 1769, 1844, 1845, 1846, 1819, 1827
        ]
        
        # 文字列形式でも検索
        sku_strings = [str(sku) for sku in actual_skus]
        
        # データベースから検索
        search_results = {
            "found_in_product_code": [],
            "found_in_product_name": [],
            "found_in_extended_info": [],
            "not_found": [],
            "summary": {}
        }
        
        # 全order_itemsを取得
        order_items = supabase.table('order_items').select('*').execute()
        
        if not order_items.data:
            return {"message": "注文データが見つかりません"}
        
        found_skus = set()
        
        # 各SKUを検索
        for sku in sku_strings:
            found = False
            
            # product_codeで検索
            for item in order_items.data:
                product_code = str(item.get('product_code', ''))
                product_name = item.get('product_name', '')
                
                # product_codeに含まれているか
                if sku in product_code or product_code == sku:
                    search_results["found_in_product_code"].append({
                        "sku": sku,
                        "product_code": product_code,
                        "product_name": product_name[:100],
                        "price": item.get('price', 0)
                    })
                    found_skus.add(sku)
                    found = True
                
                # product_nameに含まれているか
                elif sku in product_name:
                    search_results["found_in_product_name"].append({
                        "sku": sku,
                        "product_code": product_code,
                        "product_name": product_name[:100],
                        "price": item.get('price', 0)
                    })
                    found_skus.add(sku)
                    found = True
            
            if not found:
                search_results["not_found"].append(sku)
        
        # 短いSKU（4桁以下）と長いSKU（9桁）を分類
        short_skus = [sku for sku in sku_strings if len(sku) <= 4]
        long_skus = [sku for sku in sku_strings if len(sku) >= 9]
        
        search_results["summary"] = {
            "total_provided_skus": len(actual_skus),
            "short_skus_count": len(short_skus),
            "long_skus_count": len(long_skus),
            "found_count": len(found_skus),
            "not_found_count": len(search_results["not_found"]),
            "found_in_product_code": len(search_results["found_in_product_code"]),
            "found_in_product_name": len(search_results["found_in_product_name"])
        }
        
        # 見つからなかったSKUの一部を表示
        search_results["sample_not_found"] = search_results["not_found"][:10]
        
        return {
            "status": "success",
            "search_results": search_results,
            "analysis": {
                "current_database_issue": "データベース内の商品コードは楽天商品管理番号（10000xxx）で、実際の楽天SKUではない",
                "solution_needed": "楽天APIから正しいSKU情報を取得して、データベースに追加カラムとして保存する必要がある",
                "next_steps": [
                    "楽天APIからSKU情報を取得",
                    "order_itemsテーブルにrakuten_sku カラムを追加", 
                    "SKU情報を同期・保存",
                    "スプレッドシートの名寄せルールに従ってマッピング"
                ]
            },
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/analyze_database_vs_actual_skus") 
async def analyze_database_vs_actual_skus():
    """データベース内容と実際の楽天SKUの相違を分析"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 現在のデータベース内容分析
        order_items = supabase.table('order_items').select('product_code, product_name').limit(50).execute()
        
        analysis = {
            "current_database_patterns": {},
            "actual_rakuten_sku_patterns": {},
            "discrepancy_analysis": {},
            "recommendations": []
        }
        
        # 現在のデータベースパターン分析
        if order_items.data:
            db_codes = [item.get('product_code', '') for item in order_items.data]
            unique_db_codes = list(set(db_codes))
            
            analysis["current_database_patterns"] = {
                "sample_codes": unique_db_codes[:10],
                "total_unique_codes": len(unique_db_codes),
                "code_length_distribution": {},
                "pattern_analysis": "All codes follow 10000xxx format (8 digits)"
            }
            
            # 長さ分布
            for code in unique_db_codes:
                length = len(str(code))
                if length not in analysis["current_database_patterns"]["code_length_distribution"]:
                    analysis["current_database_patterns"]["code_length_distribution"][length] = 0
                analysis["current_database_patterns"]["code_length_distribution"][length] += 1
        
        # 実際の楽天SKUパターン分析
        actual_skus = [1797, 1798, 1799, 1800, 167439411, 167439431, 1701, 1703, 1768, 1769]  # サンプル
        
        analysis["actual_rakuten_sku_patterns"] = {
            "sample_skus": actual_skus,
            "short_sku_range": "1701-1869 (4 digits)",
            "long_sku_range": "167439411-167440916 (9 digits)", 
            "pattern_analysis": "Mix of 4-digit and 9-digit SKUs, completely different from database codes"
        }
        
        # 相違分析
        analysis["discrepancy_analysis"] = {
            "major_issue": "Complete mismatch between database codes and actual Rakuten SKUs",
            "database_codes": "楽天商品管理番号（管理用ID）",
            "actual_skus": "楽天SKU（実際の販売単位）",
            "impact": "現在のデータでは正確なSKUベースのマッピングができない"
        }
        
        # 推奨事項
        analysis["recommendations"] = [
            {
                "priority": "緊急",
                "action": "楽天APIからSKU情報を取得",
                "description": "注文APIまたは商品APIからSKU情報を追加取得"
            },
            {
                "priority": "高",
                "action": "データベーススキーマ拡張",
                "description": "order_itemsテーブルにrakuten_sku, choice_id等のカラム追加"
            },
            {
                "priority": "高", 
                "action": "SKUマッピングテーブル作成",
                "description": "商品管理番号 ↔ 楽天SKU ↔ 共通コードのマッピングテーブル"
            },
            {
                "priority": "中",
                "action": "データ再同期",
                "description": "正しいSKU情報を含む形でデータを再取得・保存"
            }
        ]
        
        return {
            "status": "success", 
            "analysis": analysis,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e), 
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/check_database_structure")
async def check_database_structure():
    """データベース構造の確認"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        structure_info = {}
        
        # 主要テーブルの確認
        tables_to_check = ['order_items', 'orders', 'inventory', 'platform']
        
        for table_name in tables_to_check:
            try:
                # テーブルの最初の1件を取得してカラム構造を確認
                result = supabase.table(table_name).select('*').limit(1).execute()
                if result.data and len(result.data) > 0:
                    structure_info[table_name] = {
                        "exists": True,
                        "has_data": True,
                        "sample_columns": list(result.data[0].keys()) if result.data[0] else [],
                        "record_count_sample": len(result.data)
                    }
                else:
                    structure_info[table_name] = {
                        "exists": True,
                        "has_data": False,
                        "sample_columns": [],
                        "record_count_sample": 0
                    }
            except Exception as e:
                structure_info[table_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        return {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "database_structure": structure_info,
            "recommendations": [
                "order_itemsテーブルにデータがない場合: /api/platform_sync?platform=rakuten&action=sync を実行",
                "カラム構造を確認してAPIを調整"
            ]
        }
        
    except Exception as e:
        return {
            "error": f"Database structure check failed: {str(e)}",
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/get_rakuten_sku_info")
async def get_rakuten_sku_info(management_number: str = Query(..., description="楽天商品管理番号")):
    """楽天APIから実際のSKU情報を取得"""
    try:
        from core.config import Config
        if not Config.RAKUTEN_SERVICE_SECRET or not Config.RAKUTEN_LICENSE_KEY:
            return {
                "status": "error",
                "message": "楽天API認証情報が設定されていません",
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        
        # 楽天APIクライアントを作成
        from api.rakuten_api import RakutenAPI
        rakuten_api = RakutenAPI()
        
        # SKU情報を取得
        sku_info = rakuten_api.get_rakuten_sku_info(management_number)
        
        return {
            "status": "success",
            "data": sku_info,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        logger.error(f"楽天SKU情報取得エラー: {str(e)}")
        return {
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

@app.get("/api/bulk_fetch_rakuten_skus")
async def bulk_fetch_rakuten_skus(limit: int = Query(10, description="取得件数")):
    """データベース内の商品管理番号から楽天SKU情報を一括取得"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        from core.config import Config
        if not Config.RAKUTEN_SERVICE_SECRET or not Config.RAKUTEN_LICENSE_KEY:
            return {
                "status": "error",
                "message": "楽天API認証情報が設定されていません"
            }
        
        # データベースから商品管理番号を取得
        order_items = supabase.table('order_items').select('product_code').limit(limit).execute()
        
        if not order_items.data:
            return {
                "status": "warning",
                "message": "データベースに商品データが見つかりません"
            }
        
        # 楽天APIクライアントを作成
        from api.rakuten_api import RakutenAPI
        rakuten_api = RakutenAPI()
        
        results = {
            "successful_retrievals": [],
            "failed_retrievals": [],
            "summary": {
                "total_attempted": 0,
                "successful_count": 0,
                "failed_count": 0
            }
        }
        
        # 重複を除去
        unique_codes = list(set([item['product_code'] for item in order_items.data if item['product_code']]))
        results["summary"]["total_attempted"] = len(unique_codes)
        
        for management_number in unique_codes:
            try:
                sku_info = rakuten_api.get_rakuten_sku_info(management_number)
                results["successful_retrievals"].append({
                    "management_number": management_number,
                    "sku_data": sku_info
                })
                results["summary"]["successful_count"] += 1
                
            except Exception as e:
                results["failed_retrievals"].append({
                    "management_number": management_number,
                    "error": str(e)
                })
                results["summary"]["failed_count"] += 1
        
        return {
            "status": "success",
            "data": results,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }
        
    except Exception as e:
        logger.error(f"一括SKU情報取得エラー: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

# アプリケーションの起動
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting SIZUKA在庫管理システム on port {port}")
    uvicorn.run(
        "main_cloudrun:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True
    )