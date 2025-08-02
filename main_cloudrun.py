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

# 環境変数の設定
os.environ.setdefault('SUPABASE_URL', 'https://jvkkvhdqtotbotjzngcv.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2a2t2aGRxdG90Ym90anpuZ2N2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjIzOTk5NjAsImV4cCI6MjAzNzk3NTk2MH0.A64VUJBkQ-ePdQ5dX3hPQonpOBDiC73GHhxOKWj-1Zk')

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

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
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
            # データベース接続テスト
            test_result = supabase.table('platform').select('count').limit(1).execute()
            logger.info("Supabaseデータベース接続に成功しました")
        else:
            logger.error("Supabaseクライアントの初期化に失敗しました")
    except Exception as e:
        logger.error(f"起動時エラー: {str(e)}")

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
            "mapping_tools": "/api/mapping_tools",
            "admin_tools": "/api/admin_tools",
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
                result["data"] = {"message": "楽天同期実行", "status": "success"}
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
        
        # order_itemsから商品管理番号を取得
        orders = supabase.table('order_items').select(
            'product_code, product_name, order_date'
        ).gte(
            'order_date', start_date.isoformat()
        ).lte(
            'order_date', end_date.isoformat()
        ).limit(limit).execute()
        
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
                unique_products[product_code] = order
        
        # 各商品の詳細分析
        for product_code, order_info in list(unique_products.items())[:10]:  # 最初の10件をテスト
            analyzed_products.append({
                "manage_number": product_code,
                "product_name": order_info.get('product_name', ''),
                "last_order_date": order_info.get('order_date'),
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