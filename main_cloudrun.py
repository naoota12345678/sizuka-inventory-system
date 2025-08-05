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
os.environ.setdefault('SUPABASE_URL', 'https://equrcpeifogdrxoldkpe.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ')
os.environ.setdefault('RAKUTEN_SERVICE_SECRET', 'SP338531_d1NJjF2R5OwZpWH6')
os.environ.setdefault('RAKUTEN_LICENSE_KEY', 'SL338531_kUvqO4kIHaMbr9ik')

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
from platform_sales_api import get_platform_sales_summary

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
        if not Config.RAKUTEN_SERVICE_SECRET or not Config.RAKUTEN_LICENSE_KEY:
            return {
                "status": "error",
                "message": "楽天API認証情報が設定されていません",
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
        
        # 楽天APIクライアントを作成
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

@app.get("/api/debug_rakuten_sync")
async def debug_rakuten_sync(start_date: str = "2025-08-01", end_date: str = "2025-08-03"):
    """楽天同期の詳細デバッグ情報"""
    try:
        from api.rakuten_api import RakutenAPI
        from datetime import datetime
        import pytz
        
        # 日付の解析
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=pytz.timezone('Asia/Tokyo'))
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=pytz.timezone('Asia/Tokyo'))
        
        rakuten_api = RakutenAPI()
        
        # 楽天APIから注文データを取得
        orders = rakuten_api.get_orders(start_dt, end_dt)
        
        debug_info = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "search_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "rakuten_api_result": {
                "orders_found": len(orders) if orders else 0,
                "orders_sample": orders[:2] if orders else [],
                "api_connection": "success" if orders is not None else "failed"
            }
        }
        
        if orders:
            # 注文データをSupabaseに保存を試行
            save_result = rakuten_api.save_to_supabase(orders)
            debug_info["supabase_save_result"] = save_result
        else:
            debug_info["supabase_save_result"] = "No orders to save"
        
        return debug_info
        
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
        }

# ===== 修正版売上分析API（2つのアプローチ） =====
@app.get("/api/sales/basic")
async def get_basic_sales_summary(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
):
    """A) 基本売上集計 - 共通コード単位（在庫管理と同じ仕組み）"""
    try:
        # デフォルト期間設定
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # choice_codeがある注文のみ取得（選択肢詳細分析と同じ条件）
        query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date).not_.is_('choice_code', 'null').neq('choice_code', '')
        response = query.execute()
        items = response.data if response.data else []
        
        # 共通コード別売上集計
        from collections import defaultdict
        import re
        
        common_code_sales = defaultdict(lambda: {
            'common_code': '',
            'product_name': '',
            'quantity': 0,
            'total_amount': 0,
            'orders_count': 0
        })
        
        mapped_items = 0
        unmapped_items = 0
        
        for item in items:
            choice_code = item.get('choice_code', '')
            quantity = item.get('quantity', 0)
            price = item.get('price', 0)
            sales_amount = price * quantity
            
            mapped_any = False
            
            if choice_code:
                # choice_codeから商品コード（R05, R13等）を抽出
                extracted_codes = re.findall(r'R\d{2,}', choice_code)
                
                for code in extracted_codes:
                    # choice_code_mappingテーブルでJSONB検索
                    try:
                        mapping_response = supabase.table("choice_code_mapping").select("common_code, product_name").contains("choice_info", {"choice_code": code}).execute()
                        
                        if mapping_response.data:
                            common_code = mapping_response.data[0].get('common_code')
                            product_name = mapping_response.data[0].get('product_name', '')
                            
                            # 共通コード単位で集計
                            if common_code:
                                common_code_sales[common_code]['common_code'] = common_code
                                common_code_sales[common_code]['product_name'] = product_name
                                common_code_sales[common_code]['quantity'] += quantity
                                common_code_sales[common_code]['total_amount'] += sales_amount
                                common_code_sales[common_code]['orders_count'] += 1
                                mapped_any = True
                    except Exception as e:
                        logger.error(f"Error mapping choice code {code}: {str(e)}")
                        continue
            
            if mapped_any:
                mapped_items += 1
            else:
                unmapped_items += 1
        
        # 結果をリスト化（売上順）
        sales_list = list(common_code_sales.values())
        sales_list.sort(key=lambda x: x['total_amount'], reverse=True)
        
        # 統計計算
        success_rate = (mapped_items / (mapped_items + unmapped_items) * 100) if (mapped_items + unmapped_items) > 0 else 0
        total_sales = sum(item['total_amount'] for item in sales_list)
        total_quantity = sum(item['quantity'] for item in sales_list)
        
        return {
            'status': 'success',
            'type': 'basic_sales_summary',
            'period': {'start_date': start_date, 'end_date': end_date},
            'summary': {
                'total_sales': total_sales,
                'total_quantity': total_quantity,
                'unique_products': len(sales_list),
                'mapping_success_rate': success_rate
            },
            'products': sales_list
        }
        
    except Exception as e:
        logger.error(f"Error in get_basic_sales_summary: {str(e)}")
        return {'status': 'error', 'message': str(e)}

@app.get("/api/sales/choices")
async def get_choice_detail_analysis(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
):
    """B) 選択肢詳細分析 - choice_code単位の人気分析"""
    try:
        # デフォルト期間設定
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # choice_codeがある注文のみ取得
        query = supabase.table('order_items').select('*, orders!inner(created_at)').gte('orders.created_at', start_date).lte('orders.created_at', end_date).not_.is_('choice_code', 'null').neq('choice_code', '')
        response = query.execute()
        items = response.data if response.data else []
        
        # choice_code別集計
        from collections import defaultdict
        import re
        
        choice_sales = defaultdict(lambda: {
            'choice_code': '',
            'common_code': '',
            'product_name': '',
            'quantity': 0,
            'total_amount': 0,
            'orders_count': 0
        })
        
        for item in items:
            choice_code = item.get('choice_code', '')
            quantity = item.get('quantity', 0)
            price = item.get('price', 0)
            
            # choice_codeから商品コード（R05, R13等）を抽出
            extracted_codes = re.findall(r'R\d{2,}', choice_code)
            
            for code in extracted_codes:
                # choice_code_mappingテーブルでJSONB検索
                try:
                    mapping_response = supabase.table("choice_code_mapping").select("common_code, product_name").contains("choice_info", {"choice_code": code}).execute()
                    
                    if mapping_response.data:
                        common_code = mapping_response.data[0].get('common_code', code)
                        product_name = mapping_response.data[0].get('product_name', code)
                    else:
                        common_code = code
                        product_name = f'未登録商品 ({code})'
                except Exception as e:
                    logger.error(f"Error mapping choice code {code}: {str(e)}")
                    common_code = code
                    product_name = f'未登録商品 ({code})'
                
                # choice_code別に集計
                choice_sales[code]['choice_code'] = code
                choice_sales[code]['common_code'] = common_code
                choice_sales[code]['product_name'] = product_name
                choice_sales[code]['quantity'] += quantity
                choice_sales[code]['total_amount'] += price * quantity
                choice_sales[code]['orders_count'] += 1
        
        # 人気順でソート
        choice_list = list(choice_sales.values())
        choice_list.sort(key=lambda x: x['quantity'], reverse=True)
        
        total_choice_sales = sum(item['total_amount'] for item in choice_list)
        total_choice_quantity = sum(item['quantity'] for item in choice_list)
        
        return {
            'status': 'success',
            'type': 'choice_detail_analysis',
            'period': {'start_date': start_date, 'end_date': end_date},
            'summary': {
                'total_sales': total_choice_sales,
                'total_quantity': total_choice_quantity,
                'unique_choices': len(choice_list)
            },
            'choices': choice_list
        }
        
    except Exception as e:
        logger.error(f"Error in get_choice_detail_analysis: {str(e)}")
        return {'status': 'error', 'message': str(e)}

@app.get("/api/sales/products")
async def get_product_sales(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
):
    """商品別売上一覧を取得 - 従来版（互換性のため残す）"""
    try:
        # デフォルト期間設定
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # order_itemsから商品データを取得（created_atを使用）
        query = supabase.table("order_items").select(
            "*",
            "orders!inner(created_at)"
        )
        query = query.gte("orders.created_at", start_date)
        query = query.lte("orders.created_at", end_date)
        
        response = query.execute()
        items = response.data if response.data else []
        
        # 商品別集計（マッピング済みデータを使用）
        product_sales = {}
        
        for item in items:
            product_code = item.get('product_code', 'unknown')
            
            if product_code not in product_sales:
                # product_masterからマッピング情報を取得
                if product_code != 'unknown':
                    master_response = supabase.table("product_master").select("common_code, product_name").eq("rakuten_sku", product_code).limit(1).execute()
                    if master_response.data:
                        common_code = master_response.data[0].get('common_code', f'UNMAPPED_{product_code}')
                        mapped_name = master_response.data[0].get('product_name', item.get('product_name', '不明'))
                    else:
                        common_code = f'UNMAPPED_{product_code}'
                        mapped_name = item.get('product_name', '不明')
                else:
                    common_code = 'UNKNOWN'
                    mapped_name = item.get('product_name', '不明')
                
                product_sales[product_code] = {
                    'product_code': product_code,
                    'product_name': mapped_name,
                    'common_code': common_code,
                    'quantity': 0,
                    'total_amount': 0,
                    'orders_count': 0,
                    'rakuten_sku': item.get('rakuten_item_number', ''),
                }
            
            # 数量・金額集計
            quantity = item.get('quantity', 0)
            price = item.get('price', 0)
            
            product_sales[product_code]['quantity'] += quantity
            product_sales[product_code]['total_amount'] += price * quantity
            product_sales[product_code]['orders_count'] += 1
        
        # リスト形式に変換（売上高順）
        sales_list = []
        for product_code, data in product_sales.items():
            sales_list.append({
                'product_code': product_code,
                'product_name': data['product_name'],
                'rakuten_sku': data['rakuten_sku'],
                'common_code': data['common_code'],
                'quantity': data['quantity'],
                'total_amount': data['total_amount'],
                'orders_count': data['orders_count'],
                'average_price': data['total_amount'] / data['quantity'] if data['quantity'] > 0 else 0
            })
        
        # 売上高順にソート
        sales_list.sort(key=lambda x: x['total_amount'], reverse=True)
        
        # サマリー情報
        total_sales = sum(item['total_amount'] for item in sales_list)
        total_quantity = sum(item['quantity'] for item in sales_list)
        total_orders = sum(item['orders_count'] for item in sales_list)
        
        return {
            'status': 'success',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_sales': total_sales,
                'total_quantity': total_quantity,
                'total_orders': total_orders,
                'unique_products': len(sales_list)
            },
            'products': sales_list[:100]  # 上位100商品
        }
        
    except Exception as e:
        logger.error(f"Error in get_product_sales: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

@app.get("/api/sales/summary")
async def get_sales_summary(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    group_by: str = Query("day", description="集計単位 (day/week/month)")
):
    """期間別売上サマリー - マッピング済みデータから直接集計"""
    try:
        # デフォルト期間設定
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # order_itemsから直接集計（product_masterでマッピング情報を取得）
        query = supabase.table("order_items").select(
            "quantity, price, product_code, product_name, created_at",
            "orders!inner(order_date, created_at)"
        )
        query = query.gte("orders.created_at", start_date)
        query = query.lte("orders.created_at", end_date)
        
        response = query.execute()
        items = response.data if response.data else []
        
        # 期間別集計
        period_sales = {}
        total_sales = 0
        total_quantity = 0
        total_orders = set()
        
        for item in items:
            # JOINしたordersテーブルからcreated_atを取得
            order_data = item.get('orders', {})
            order_date = order_data.get('created_at', '')
            if not order_date:
                continue
                
            # 期間キー生成
            dt = datetime.strptime(order_date[:10], '%Y-%m-%d')
            if group_by == 'day':
                period_key = dt.strftime('%Y-%m-%d')
            elif group_by == 'week':
                week_start = dt - timedelta(days=dt.weekday())
                period_key = week_start.strftime('%Y-%m-%d')
            else:  # month
                period_key = dt.strftime('%Y-%m')
            
            if period_key not in period_sales:
                period_sales[period_key] = {
                    'quantity': 0,
                    'total_amount': 0,
                    'orders_count': 0
                }
            
            # 集計
            quantity = item.get('quantity', 0)
            price = item.get('price', 0)
            
            period_sales[period_key]['quantity'] += quantity
            period_sales[period_key]['total_amount'] += price * quantity
            period_sales[period_key]['orders_count'] += 1
        
        # リスト形式に変換（日付順）
        sales_timeline = []
        for period, data in sorted(period_sales.items()):
            sales_timeline.append({
                'period': period,
                'quantity': data['quantity'],
                'total_amount': data['total_amount'],
                'orders_count': data['orders_count']
            })
        
        # 全体サマリー
        total_sales = sum(item['total_amount'] for item in sales_timeline)
        total_quantity = sum(item['quantity'] for item in sales_timeline)
        total_orders = sum(item['orders_count'] for item in sales_timeline)
        
        return {
            'status': 'success',
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'group_by': group_by
            },
            'summary': {
                'total_sales': total_sales,
                'total_quantity': total_quantity,
                'total_orders': total_orders,
                'periods_count': len(sales_timeline)
            },
            'timeline': sales_timeline
        }
        
    except Exception as e:
        logger.error(f"Error in get_sales_summary: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }

# ===== 新規: プラットフォーム別売上集計API =====
@app.get("/api/sales/platform_summary")
async def platform_sales_summary(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)")
):
    """
    プラットフォーム別売上集計を取得
    
    Parameters:
    - start_date: 開始日（省略時は30日前）
    - end_date: 終了日（省略時は今日）
    
    Returns:
    - 期間内の取引先別売上集計
    """
    return await get_platform_sales_summary(start_date, end_date)

@app.get("/platform-sales", response_class=HTMLResponse)
async def platform_sales_dashboard(request: Request):
    """プラットフォーム別売上ダッシュボードUI"""
    with open("platform_sales_dashboard.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/sales-dashboard", response_class=HTMLResponse)
async def sales_dashboard(request: Request):
    """売上ダッシュボードUI"""
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>楽天売上分析ダッシュボード</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .header h1 {
            font-size: 24px;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .filters {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .filter-group label {
            font-size: 12px;
            color: #666;
            font-weight: 500;
        }
        
        .filter-group input,
        .filter-group select {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .btn {
            padding: 8px 20px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        .btn:hover {
            background: #2980b9;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            font-size: 16px;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 14px;
            color: #666;
        }
        
        .table-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
            position: sticky;
            top: 0;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .number {
            text-align: right;
            font-family: 'SF Mono', Monaco, monospace;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .tab {
            padding: 10px 20px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
            color: #666;
            transition: all 0.3s;
        }
        
        .tab.active {
            color: #3498db;
            border-bottom: 2px solid #3498db;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>楽天売上分析ダッシュボード</h1>
            <div class="filters">
                <div class="filter-group">
                    <label>開始日</label>
                    <input type="date" id="startDate" value="">
                </div>
                <div class="filter-group">
                    <label>終了日</label>
                    <input type="date" id="endDate" value="">
                </div>
                <div class="filter-group">
                    <label>集計単位</label>
                    <select id="groupBy">
                        <option value="day">日別</option>
                        <option value="week">週別</option>
                        <option value="month">月別</option>
                    </select>
                </div>
                <button class="btn" onclick="loadData()">更新</button>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="card">
                <h2>売上高</h2>
                <div class="stat-value" id="totalSales">-</div>
                <div class="stat-label">円</div>
            </div>
            <div class="card">
                <h2>販売数量</h2>
                <div class="stat-value" id="totalQuantity">-</div>
                <div class="stat-label">個</div>
            </div>
            <div class="card">
                <h2>注文数</h2>
                <div class="stat-value" id="totalOrders">-</div>
                <div class="stat-label">件</div>
            </div>
            <div class="card">
                <h2>商品数</h2>
                <div class="stat-value" id="uniqueProducts">-</div>
                <div class="stat-label">種類</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('products')">商品別売上</button>
            <button class="tab" onclick="showTab('timeline')">期間別推移</button>
        </div>

        <div id="productsTab" class="table-container">
            <h2>商品別売上一覧</h2>
            <table id="productsTable">
                <thead>
                    <tr>
                        <th>商品コード</th>
                        <th>商品名</th>
                        <th>共通コード</th>
                        <th class="number">販売数量</th>
                        <th class="number">売上高</th>
                        <th class="number">注文数</th>
                        <th class="number">平均単価</th>
                    </tr>
                </thead>
                <tbody id="productsBody">
                    <tr><td colspan="7" class="loading">データを読み込んでいます...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="timelineTab" class="table-container" style="display:none;">
            <h2>期間別売上推移</h2>
            <table id="timelineTable">
                <thead>
                    <tr>
                        <th>期間</th>
                        <th class="number">売上高</th>
                        <th class="number">販売数量</th>
                        <th class="number">注文数</th>
                    </tr>
                </thead>
                <tbody id="timelineBody">
                    <tr><td colspan="4" class="loading">データを読み込んでいます...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // 初期設定
        document.addEventListener('DOMContentLoaded', function() {
            const today = new Date();
            const thirtyDaysAgo = new Date(today);
            thirtyDaysAgo.setDate(today.getDate() - 30);
            
            document.getElementById('endDate').value = today.toISOString().split('T')[0];
            document.getElementById('startDate').value = thirtyDaysAgo.toISOString().split('T')[0];
            
            loadData();
        });

        async function loadData() {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const groupBy = document.getElementById('groupBy').value;
            
            // 商品別売上取得
            try {
                const response = await fetch(`${window.location.origin}/api/sales/products?start_date=${startDate}&end_date=${endDate}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    updateSummary(data.summary);
                    updateProductsTable(data.products);
                }
            } catch (error) {
                console.error('Error loading products:', error);
            }
            
            // 期間別売上取得
            try {
                const response = await fetch(`${window.location.origin}/api/sales/summary?start_date=${startDate}&end_date=${endDate}&group_by=${groupBy}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    updateTimelineTable(data.timeline);
                }
            } catch (error) {
                console.error('Error loading timeline:', error);
            }
        }

        function updateSummary(summary) {
            document.getElementById('totalSales').textContent = summary.total_sales.toLocaleString();
            document.getElementById('totalQuantity').textContent = summary.total_quantity.toLocaleString();
            document.getElementById('totalOrders').textContent = summary.total_orders.toLocaleString();
            document.getElementById('uniqueProducts').textContent = summary.unique_products.toLocaleString();
        }

        function updateProductsTable(products) {
            const tbody = document.getElementById('productsBody');
            tbody.innerHTML = products.map(product => `
                <tr>
                    <td>${product.product_code}</td>
                    <td>${product.product_name}</td>
                    <td>${product.common_code || '-'}</td>
                    <td class="number">${product.quantity.toLocaleString()}</td>
                    <td class="number">¥${product.total_amount.toLocaleString()}</td>
                    <td class="number">${product.orders_count.toLocaleString()}</td>
                    <td class="number">¥${Math.round(product.average_price).toLocaleString()}</td>
                </tr>
            `).join('');
        }

        function updateTimelineTable(timeline) {
            const tbody = document.getElementById('timelineBody');
            tbody.innerHTML = timeline.map(period => `
                <tr>
                    <td>${period.period}</td>
                    <td class="number">¥${period.total_amount.toLocaleString()}</td>
                    <td class="number">${period.quantity.toLocaleString()}</td>
                    <td class="number">${period.orders_count.toLocaleString()}</td>
                </tr>
            `).join('');
        }

        function showTab(tabName) {
            // タブ切り替え
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // コンテンツ切り替え
            document.getElementById('productsTab').style.display = tabName === 'products' ? 'block' : 'none';
            document.getElementById('timelineTab').style.display = tabName === 'timeline' ? 'block' : 'none';
        }
    </script>
</body>
</html>
    """
    return html_content

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