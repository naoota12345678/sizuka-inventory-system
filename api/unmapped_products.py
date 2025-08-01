from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime
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

@app.get("/api/check_unmapped_products")
async def check_unmapped_products():
    """マッピングできない商品をチェック"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "unmapped_products": [],
            "mapping_status": {}
        }
        
        # 1. 楽天注文データから商品を取得
        rakuten_products = await get_rakuten_products()
        results["mapping_status"]["rakuten"] = rakuten_products
        
        # 2. 他のプラットフォームがあれば追加
        # Amazon, ColorME, Airegi等
        
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

async def get_rakuten_products():
    """楽天商品のマッピング状況をチェック"""
    try:
        # 楽天注文商品データを取得
        order_items = supabase.table('order_items').select('item_name, item_price, sku').execute()
        
        if not order_items.data:
            return {
                "platform": "rakuten",
                "total_products": 0,
                "mapped_products": 0,
                "unmapped_products": [],
                "message": "楽天注文データがありません"
            }
        
        # 商品の重複除去
        unique_products = {}
        for item in order_items.data:
            sku = item.get('sku') or item.get('item_name', 'unknown')
            if sku not in unique_products:
                unique_products[sku] = {
                    "sku": sku,
                    "item_name": item.get('item_name', ''),
                    "item_price": item.get('item_price', 0)
                }
        
        # マッピング状況をチェック
        mapped_count = 0
        unmapped_products = []
        
        for sku, product in unique_products.items():
            # プラットフォームマッピングテーブルでチェック
            mapping_result = supabase.table('platform_product_mapping').select('common_code').eq('platform_name', 'rakuten').eq('platform_product_code', sku).execute()
            
            if mapping_result.data:
                mapped_count += 1
                product["common_code"] = mapping_result.data[0]['common_code']
                product["mapping_status"] = "mapped"
            else:
                product["mapping_status"] = "unmapped"
                unmapped_products.append(product)
        
        return {
            "platform": "rakuten",
            "total_products": len(unique_products),
            "mapped_products": mapped_count,
            "unmapped_count": len(unmapped_products),
            "unmapped_products": unmapped_products
        }
        
    except Exception as e:
        return {
            "platform": "rakuten",
            "error": str(e)
        }

@app.post("/api/add_product_mapping")
async def add_product_mapping(
    platform_name: str = Query(..., description="プラットフォーム名"),
    platform_product_code: str = Query(..., description="プラットフォーム商品コード"),
    common_code: str = Query(..., description="共通コード"),
    platform_product_name: str = Query("", description="プラットフォーム商品名")
):
    """手動で商品マッピングを追加"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        # 重複チェック
        existing = supabase.table('platform_product_mapping').select('id').eq('platform_name', platform_name).eq('platform_product_code', platform_product_code).execute()
        
        if existing.data:
            # 既存の場合は更新
            result = supabase.table('platform_product_mapping').update({
                'common_code': common_code,
                'platform_product_name': platform_product_name,
                'updated_at': datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }).eq('platform_name', platform_name).eq('platform_product_code', platform_product_code).execute()
            
            action = "updated"
        else:
            # 新規追加
            result = supabase.table('platform_product_mapping').insert({
                'platform_name': platform_name,
                'platform_product_code': platform_product_code,
                'common_code': common_code,
                'platform_product_name': platform_product_name,
                'is_active': True
            }).execute()
            
            action = "added"
        
        return {
            "status": "success",
            "action": action,
            "mapping": {
                "platform_name": platform_name,
                "platform_product_code": platform_product_code,
                "common_code": common_code,
                "platform_product_name": platform_product_name
            },
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

@app.get("/api/reprocess_sales_data")
async def reprocess_sales_data(
    start_date: Optional[str] = Query("2025-02-10", description="再処理開始日"),
    end_date: Optional[str] = Query(None, description="再処理終了日（未指定で今日まで）")
):
    """売上データの再処理（マッピング追加後）"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        if not end_date:
            end_date = datetime.now(pytz.timezone('Asia/Tokyo')).date().isoformat()
        
        results = {
            "start_date": start_date,
            "end_date": end_date,
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "reprocessing_results": {}
        }
        
        # 楽天データの再処理
        rakuten_result = await reprocess_rakuten_sales(start_date, end_date)
        results["reprocessing_results"]["rakuten"] = rakuten_result
        
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

async def reprocess_rakuten_sales(start_date: str, end_date: str):
    """楽天売上データの再処理（全売上をそのまま集計）"""
    try:
        # 指定期間の注文を取得
        orders = supabase.table('orders').select('*').gte('order_datetime', start_date).lte('order_datetime', end_date + 'T23:59:59').execute()
        
        if not orders.data:
            return {
                "status": "warning",
                "message": "再処理対象の注文データがありません"
            }
        
        processed_count = 0
        unmapped_count = 0
        error_count = 0
        
        for order in orders.data:
            order_id = order['id']
            
            # この注文の商品を取得
            order_items = supabase.table('order_items').select('*').eq('order_id', order_id).execute()
            
            if not order_items.data:
                continue
            
            for item in order_items.data:
                sku = item.get('sku') or item.get('item_name', '')
                
                # マッピングを確認
                mapping = supabase.table('platform_product_mapping').select('common_code').eq('platform_name', 'rakuten').eq('platform_product_code', sku).execute()
                
                # 共通コードを決定（マッピングがない場合は'UNMAPPED_'を付加）
                if mapping.data:
                    common_code = mapping.data[0]['common_code']
                else:
                    common_code = f'UNMAPPED_{sku}'
                    unmapped_count += 1
                
                # sales_masterに挿入（マッピング有無に関係なく全売上を記録）
                existing_sale = supabase.table('sales_master').select('id').eq('platform_order_id', order.get('order_number')).eq('common_code', common_code).execute()
                
                if not existing_sale.data:
                    # 新規追加
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
                    
                    try:
                        supabase.table('sales_master').insert(sale_record).execute()
                        processed_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Sales insertion error: {str(e)}")
                else:
                    # 既存データのため更新
                    sale_record = {
                        'quantity': item.get('units', 1),
                        'unit_price': float(item.get('item_price', 0)),
                        'total_amount': float(item.get('item_price', 0)) * item.get('units', 1),
                        'is_mapped': mapping.data is not None,
                        'updated_at': datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
                    }
                    
                    try:
                        supabase.table('sales_master').update(sale_record).eq('id', existing_sale.data[0]['id']).execute()
                        processed_count += 1
                    except Exception as e:
                        error_count += 1
        
        return {
            "status": "success",
            "processed_count": processed_count,
            "unmapped_count": unmapped_count,
            "error_count": error_count,
            "message": f"楽天売上データ再処理完了: 全{processed_count}件を記録（未マッピング{unmapped_count}件含む）"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"楽天売上データ再処理エラー: {str(e)}"
        }

@app.get("/api/mapping_suggestions")
async def mapping_suggestions():
    """マッピング候補の提案"""
    try:
        if not supabase:
            return {"error": "Database connection not configured"}
        
        results = {
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat(),
            "suggestions": []
        }
        
        # 商品名の類似性でマッピング候補を提案
        unmapped = await get_rakuten_products()
        
        if unmapped.get("unmapped_products"):
            product_masters = supabase.table('product_mapping_master').select('common_code, product_name').execute()
            
            if product_masters.data:
                for unmapped_product in unmapped["unmapped_products"]:
                    item_name = unmapped_product["item_name"]
                    
                    # 簡単な類似性チェック
                    suggestions = []
                    for master in product_masters.data:
                        master_name = master["product_name"]
                        
                        # キーワードマッチング
                        if any(keyword in item_name for keyword in master_name.split()):
                            suggestions.append({
                                "common_code": master["common_code"],
                                "product_name": master_name,
                                "confidence": "medium"
                            })
                    
                    if suggestions:
                        results["suggestions"].append({
                            "unmapped_product": unmapped_product,
                            "suggested_mappings": suggestions[:3]  # 上位3件
                        })
        
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