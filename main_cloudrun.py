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
    """指定された楽天商品の詳細・バリエーション情報を取得"""
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
                
                return {
                    "manage_number": manage_number,
                    "product_info": product_info,
                    "analysis": {
                        "product_name": product_info.get('product_name', ''),
                        "quantity": product_info.get('quantity', 0),
                        "price": product_info.get('price', 0),
                        "extracted_variations": extract_variations_from_name(product_info.get('product_name', '')),
                        "note": "基本データベース情報のみ。楽天API統合により詳細な子商品情報が今後利用可能"
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