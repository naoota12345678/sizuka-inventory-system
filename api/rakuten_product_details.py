#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天商品詳細取得API - 子商品・バリエーション情報を含む
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import pytz
import os
import logging
from supabase import create_client, Client
from typing import Optional, List, Dict, Any
import json
import base64
import httpx

logger = logging.getLogger(__name__)

app = FastAPI()

# Supabase接続
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

class RakutenProductAPI:
    """楽天商品詳細API"""
    
    def __init__(self):
        self.service_secret = os.getenv('RAKUTEN_SERVICE_SECRET')
        self.license_key = os.getenv('RAKUTEN_LICENSE_KEY')
        
        if not self.service_secret or not self.license_key:
            raise ValueError("楽天API認証情報が設定されていません")
        
        auth_string = f"{self.service_secret}:{self.license_key}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        self.headers = {
            'Authorization': f'ESA {encoded_auth}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        self.base_url = 'https://api.rms.rakuten.co.jp/es/2.0'

    def get_product_details(self, manage_number: str) -> Dict[str, Any]:
        """商品詳細情報を取得（子商品・バリエーション含む）"""
        url = f'{self.base_url}/items/get'
        
        request_data = {
            "itemUrl": manage_number  # 商品管理番号
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    headers=self.headers,
                    json=request_data,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail="楽天API認証に失敗しました")
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"商品詳細取得エラー ({manage_number}): {str(e)}")
            return {"error": str(e)}

    def get_product_variations(self, manage_number: str) -> Dict[str, Any]:
        """商品のバリエーション情報を取得"""
        try:
            product_details = self.get_product_details(manage_number)
            
            if "error" in product_details:
                return product_details
            
            # バリエーション情報の抽出
            item_data = product_details.get('item', {})
            variations = []
            
            # 選択肢がある場合
            if 'optionList' in item_data:
                for option in item_data['optionList']:
                    variation_info = {
                        "option_name": option.get('optionName', ''),
                        "option_id": option.get('optionId', ''),
                        "values": []
                    }
                    
                    if 'optionValueList' in option:
                        for value in option['optionValueList']:
                            variation_info["values"].append({
                                "value_name": value.get('optionValueName', ''),
                                "value_id": value.get('optionValueId', ''),
                                "choice_code": value.get('choiceCode', ''),
                                "sku": value.get('sku', ''),
                                "stock": value.get('inventory', 0),
                                "price": value.get('price', 0)
                            })
                    
                    variations.append(variation_info)
            
            return {
                "manage_number": manage_number,
                "product_name": item_data.get('itemName', ''),
                "variations": variations,
                "total_variations": len(variations),
                "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
            }
            
        except Exception as e:
            logger.error(f"バリエーション取得エラー ({manage_number}): {str(e)}")
            return {"error": str(e)}

@app.get("/api/rakuten_product_details")
async def get_rakuten_product_details(
    manage_number: str = Query(..., description="楽天商品管理番号"),
    include_variations: bool = Query(True, description="バリエーション情報を含むか")
):
    """楽天商品詳細取得（子商品・バリエーション情報含む）"""
    try:
        api = RakutenProductAPI()
        
        if include_variations:
            result = api.get_product_variations(manage_number)
        else:
            result = api.get_product_details(manage_number)
        
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
                    "期間を長くして再実行してください",
                    "まず楽天APIから注文データを同期してください"
                ]
            }
        
        api = RakutenProductAPI()
        analyzed_products = []
        unique_products = {}
        
        # 重複を除去
        for order in orders.data:
            product_code = order.get('product_code', '')
            if product_code and product_code not in unique_products:
                unique_products[product_code] = order
        
        # 各商品の詳細分析
        for product_code, order_info in unique_products.items():
            try:
                product_analysis = api.get_product_variations(product_code)
                product_analysis["order_info"] = {
                    "last_order_date": order_info.get('order_date'),
                    "product_name_in_order": order_info.get('product_name')
                }
                analyzed_products.append(product_analysis)
                
            except Exception as e:
                logger.error(f"商品分析エラー ({product_code}): {str(e)}")
                analyzed_products.append({
                    "manage_number": product_code,
                    "error": str(e),
                    "order_info": order_info
                })
        
        return {
            "analysis_period": f"{start_date.strftime('%Y-%m-%d')} から {end_date.strftime('%Y-%m-%d')}",
            "total_unique_products": len(unique_products),
            "analyzed_products": analyzed_products,
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