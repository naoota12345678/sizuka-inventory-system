#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天API処理モジュール
注文データの取得と保存
"""

import base64
import json
import logging
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import httpx
import pytz
from fastapi import HTTPException

from core.config import Config
from core.database import Database
from core.utils import extract_product_code_prefix, extract_sku_data, extract_selected_choices

logger = logging.getLogger(__name__)

class RakutenAPI:
    """楽天APIクライアント"""
    
    def __init__(self):
        self.service_secret = Config.RAKUTEN_SERVICE_SECRET
        self.license_key = Config.RAKUTEN_LICENSE_KEY
        
        if not self.service_secret or not self.license_key:
            raise ValueError("楽天API認証情報が設定されていません")
        
        # 認証ヘッダーの生成
        auth_string = f"{self.service_secret}:{self.license_key}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        
        self.headers = {
            'Authorization': f'ESA {encoded_auth}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        self.jst = pytz.timezone('Asia/Tokyo')
        self.base_url = 'https://api.rms.rakuten.co.jp/es/2.0'

    def get_orders(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """注文データの検索"""
        url = f'{self.base_url}/purchaseItem/searchOrderItem/'
        
        jst_st = start_date.astimezone(self.jst).strftime("%Y-%m-%dT%H:%M:%S+0900")
        jst_ed = end_date.astimezone(self.jst).strftime("%Y-%m-%dT%H:%M:%S+0900")

        search_data = {
            "dateType": 1,
            "startDatetime": jst_st,
            "endDatetime": jst_ed,
            "orderProgressList": [100, 200, 300, 400, 500, 600, 700],
            "PaginationRequestModel": {
                "requestRecordsAmount": 1000,
                "requestPage": 1
            }
        }

        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    headers=self.headers,
                    json=search_data,
                    timeout=30.0
                )

                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail=f"認証に失敗しました: {response.text}")

                response.raise_for_status()
                # 文字エンコード問題を修正
                response.encoding = 'utf-8'
                data = response.json()
                order_numbers = data.get('orderNumberList', [])

                if order_numbers:
                    return self.get_order_details(order_numbers)
                return []

        except Exception as e:
            logger.error(f"注文取得エラー: {str(e)}")
            raise

    def get_order_details(self, order_numbers: List[str]) -> List[Dict]:
        """注文の詳細情報を取得"""
        url = f'{self.base_url}/purchaseItem/getOrderItem/'
        chunk_size = 100
        all_orders = []
        
        for i in range(0, len(order_numbers), chunk_size):
            chunk = order_numbers[i:i + chunk_size]
            order_data = {'orderNumberList': chunk}
            
            try:
                with httpx.Client() as client:
                    logger.info(f"注文詳細を取得中: {i+1} から {i+len(chunk)} 件目")
                    
                    response = client.post(
                        url,
                        headers=self.headers,
                        json=order_data,
                        timeout=30.0
                    )
                    
                    if response.status_code == 401:
                        raise HTTPException(status_code=401, detail="認証に失敗しました")
                    
                    response.raise_for_status()
                    # 文字エンコード問題を修正
                    response.encoding = 'utf-8'
                    data = response.json()
                    
                    if 'OrderModelList' in data:
                        all_orders.extend(data['OrderModelList'])
                    
            except Exception as e:
                logger.error(f"チャンク {i//chunk_size + 1} の詳細取得エラー: {str(e)}")
                continue
        
        return all_orders

    def save_to_supabase(self, orders: List[Dict]) -> Dict[str, Any]:
        """注文データをSupabaseに保存"""
        MAX_RETRIES = 3
        RETRY_DELAY = 1
        
        supabase = Database.get_client()
        if not supabase:
            raise ValueError("Supabaseクライアントが初期化されていません")
        
        try:
            # 楽天のplatform_idを取得
            platform_response = self._get_platform_id_with_retry()
            rakuten_platform_id = platform_response.data[0]['id']
            
            success_count = 0
            error_count = 0
            items_success = 0
            items_error = 0
            failed_orders = []
            processed_orders = set()

            for order in orders:
                order_number = order.get('orderNumber')
                if not order_number or order_number in processed_orders:
                    logger.warning(f"無効または重複した注文をスキップ: {order_number}")
                    continue
                    
                processed_orders.add(order_number)
                
                try:
                    # 注文データの準備
                    order_data = self._prepare_order_data(order, rakuten_platform_id)

                    # 注文データの保存（重複チェック付き）
                    # 既存注文をチェック
                    existing = Database.get_client().table("orders").select("id").eq("order_number", order_data["order_number"]).execute()
                    
                    if existing.data:
                        # 既存の注文があれば更新
                        order_result = Database.get_client().table("orders").update(order_data).eq("order_number", order_data["order_number"]).execute()
                    else:
                        # 新規注文として挿入
                        order_result = Database.get_client().table("orders").insert(order_data).execute()

                    if not order_result.data:
                        raise Exception(f"注文の保存に失敗: {order_number}")

                    order_id = order_result.data[0]["id"]
                    logger.info(f"注文 {order_number} を保存しました (ID: {order_id})")

                    # 注文商品情報の保存
                    items_count = self._save_order_items(order, order_id)
                    items_success += items_count['success']
                    items_error += items_count['error']

                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"注文 {order_number} の処理エラー: {str(e)}")
                    error_count += 1
                    failed_orders.append({
                        'order_number': order_number,
                        'error': str(e)
                    })

            result = {
                'total_orders': len(orders),
                'success_count': success_count,
                'error_count': error_count,
                'items_success': items_success,
                'items_error': items_error,
                'success_rate': f"{(success_count / len(orders) * 100):.2f}%" if orders else "0%",
                'failed_orders': failed_orders
            }

            logger.info(f"同期完了: {json.dumps(result, indent=2)}")
            return result

        except Exception as e:
            logger.error(f"save_to_supabaseで重大なエラー: {str(e)}")
            raise

    def _prepare_order_data(self, order: Dict, platform_id: int) -> Dict:
        """注文データを準備（現在のスキーマに合わせて調整）"""
        # 現在のordersテーブルのスキーマに合わせる
        # カラム: id, platform_id, order_number, order_date, total_amount, status, created_at
        return {
            "platform_id": platform_id,
            "order_number": order["orderNumber"],
            "order_date": order.get("orderDatetime") or order.get("shopOrderCfmDatetime"),
            "total_amount": float(order.get("totalPrice", 0)),
            "status": "completed",  # 楽天から取得したデータは基本的に完了済み
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    def _save_order_items(self, order: Dict, order_id: int) -> Dict[str, int]:
        """注文商品を保存"""
        items = []
        for package in order.get("PackageModelList", []):
            items.extend(package.get("ItemModelList", []))
        
        if not items:
            logger.warning(f"注文に商品が見つかりません: {order.get('orderNumber')}")
            return {"success": 0, "error": 0}

        success_count = 0
        error_count = 0
        MAX_RETRIES = 3

        for item in items:
            for attempt in range(MAX_RETRIES):
                try:
                    # 商品データの処理
                    is_parent = item.get("itemType") == 1
                    
                    if is_parent:
                        # 親商品とその子商品を保存
                        saved = self._save_parent_and_children(item, order_id, order.get('orderNumber'))
                        success_count += saved
                    else:
                        # 通常商品を保存
                        item_data = self._prepare_item_data(item, order_id, is_parent=False)
                        
                        # 商品データの保存
                        item_result = Database.get_client().table("order_items").insert(item_data).execute()
                        
                        if not item_result.data:
                            raise Exception(f"商品データの保存に失敗: {item_data['product_code']}")
                        
                        logger.info(f"商品 {item_data['product_code']} を保存しました")
                        
                        # SKUマッピングの自動保存（楽天SKUが取得できた場合）
                        if item_data.get('rakuten_sku'):
                            self.save_sku_mapping(
                                management_number=item_data['product_code'],
                                rakuten_sku=item_data['rakuten_sku'],
                                choice_code=item_data.get('choice_code', ''),
                                notes=f"Auto-saved from order {order_number}"
                            )
                        
                        success_count += 1
                        
                    break

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"[DEBUG] 商品保存エラー: {error_msg}")
                    logger.error(f"[DEBUG] スタックトレース: {traceback.format_exc()}")
                    
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"リトライ中... 試行 {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(1)
                    else:
                        error_count += 1
                        logger.error(f"すべてのリトライに失敗しました")

        return {"success": success_count, "error": error_count}

    def _prepare_item_data(self, item: Dict, order_id: int, is_parent: bool = False, is_child: bool = False, parent_product_code: str = "") -> Dict:
        """商品データを準備（拡張版：楽天情報を直接カラムに保存）"""
        
        item_name = item.get("itemName", "")
        quantity = int(item.get("units", 0))
        unit_price = float(item.get("price", 0))
        
        # 楽天APIから取得可能な豊富な情報を抽出
        jan_code = item.get("janCode", "")
        category_path = item.get("categoryPathName", "")
        brand_name = item.get("brandName", "")
        
        # より詳細な商品コード（楽天の管理商品番号）
        rakuten_item_number = item.get("itemNumber", "")
        rakuten_variant_id = item.get("variantId", "")
        
        # 重要: 実際の楽天SKUを抽出（優先順位付き）
        rakuten_sku = ""
        sku_type = "simple"
        
        # 1. 最優先: itemNumberから楽天SKUを取得
        if rakuten_item_number:
            rakuten_sku = str(rakuten_item_number)
            sku_type = "item_number"
        # 2. 次優先: skuIdフィールドから取得
        elif "skuId" in item and item.get("skuId"):
            rakuten_sku = str(item.get("skuId", ""))
            sku_type = "sku_id"
        # 3. SkuModelListから取得
        elif "SkuModelList" in item:
            sku_models = item.get("SkuModelList", [])
            if sku_models and len(sku_models) > 0:
                sku_model = sku_models[0]
                if sku_model.get("skuId"):
                    rakuten_sku = str(sku_model.get("skuId", ""))
                    sku_type = "sku_model_list"
                elif sku_model.get("variantId"):
                    rakuten_sku = str(sku_model.get("variantId", ""))
                    sku_type = "variant_from_model"
                if len(sku_models) > 1:
                    sku_type += "_multi"
        # 4. 最後の手段: variantId
        elif rakuten_variant_id:
            rakuten_sku = rakuten_variant_id
            sku_type = "variant_id"
        
        # 商品重量・サイズ情報
        weight = item.get("weight", "")
        size_info = item.get("sizeInfo", "")
        
        # ショップ情報
        shop_item_code = item.get("shopItemCode", "")
        
        # 楽天APIのselectedChoiceフィールドから選択肢コードを正確に抽出
        choice_code = ""
        selected_choices = []
        
        # selectedChoiceフィールドから直接選択肢コードを取得
        if "selectedChoice" in item and item["selectedChoice"]:
            selected_choice_data = item["selectedChoice"]
            if isinstance(selected_choice_data, list):
                # リスト形式の場合
                for choice in selected_choice_data:
                    if isinstance(choice, dict):
                        choice_name = choice.get("choiceName", "")
                        choice_value = choice.get("choiceValue", "")
                        if choice_name and choice_value:
                            # 文字エンコード修正
                            try:
                                choice_name = choice_name.encode('latin1').decode('utf-8', errors='ignore')
                                choice_value = choice_value.encode('latin1').decode('utf-8', errors='ignore')
                            except:
                                pass  # エンコード修正に失敗した場合はそのまま使用
                            selected_choices.append(f"{choice_name}:{choice_value}")
                choice_code = ",".join(selected_choices)
            elif isinstance(selected_choice_data, dict):
                # 辞書形式の場合
                choice_name = selected_choice_data.get("choiceName", "")
                choice_value = selected_choice_data.get("choiceValue", "")
                if choice_name and choice_value:
                    # 文字エンコード修正
                    try:
                        choice_name = choice_name.encode('latin1').decode('utf-8', errors='ignore')
                        choice_value = choice_value.encode('latin1').decode('utf-8', errors='ignore')
                    except:
                        pass  # エンコード修正に失敗した場合はそのまま使用
                    choice_code = f"{choice_name}:{choice_value}"
            elif isinstance(selected_choice_data, str):
                # 文字列形式の場合
                try:
                    choice_code = selected_choice_data.encode('latin1').decode('utf-8', errors='ignore')
                except:
                    choice_code = selected_choice_data
        
        # selectedChoiceが空の場合、商品名から抽出を試行（フォールバック）
        if not choice_code:
            from core.utils import extract_choice_code_from_name
            choice_code = extract_choice_code_from_name(item_name)
        
        # その他の詳細情報
        item_description = item.get("itemDescription", "")
        item_url = item.get("itemUrl", "")
        original_price = float(item.get("originalPrice", 0))
        discount_price = float(item.get("discountPrice", 0))
        
        return {
            "order_id": order_id,
            "product_code": str(item.get("itemId", "")),
            "product_name": item_name,
            "quantity": quantity,
            "price": unit_price,
            "created_at": datetime.now(timezone.utc).isoformat(),
            
            # 楽天特有の情報を直接カラムに保存
            "choice_code": choice_code,
            "item_type": 1 if is_parent else 0,
            "rakuten_variant_id": rakuten_variant_id,
            "rakuten_item_number": rakuten_sku,  # 実際のSKUを保存
            "shop_item_code": shop_item_code,
            "jan_code": jan_code,
            "category_path": category_path,
            "brand_name": brand_name,
            "weight_info": weight,
            "size_info": size_info,
            
            # 重要: 実際の楽天SKU情報
            "rakuten_sku": rakuten_sku,
            "sku_type": sku_type,
            
            # 詳細情報はJSONBに保存
            "extended_rakuten_data": {
                "item_description": item_description[:500],  # 500文字まで
                "item_url": item_url,
                "original_price": original_price,
                "discount_price": discount_price,
                "is_parent": is_parent,
                "is_child": is_child,
                "parent_product_code": parent_product_code,
                "raw_sku_data": {
                    "original_sku_info": item.get("SkuModelList", []),
                    "extracted_sku": rakuten_sku,
                    "extraction_method": "skuId" if "skuId" in item else "SkuModelList" if "SkuModelList" in item else "variantId"
                }
            }
        }

    def _save_parent_and_children(self, parent_item: Dict, order_id: int, order_number: str) -> int:
        """親商品とその子商品を保存（現在のスキーマに合わせて調整）"""
        saved_count = 0
        
        # 親商品のデータを保存
        parent_data = self._prepare_item_data(parent_item, order_id, is_parent=True)
        parent_result = Database.get_client().table("order_items").insert(parent_data).execute()
        
        if not parent_result.data:
            raise Exception(f"親商品の保存に失敗: {parent_data['product_code']}")
        
        logger.info(f"親商品 {parent_data['product_code']} を保存しました (注文: {order_number})")
        
        # 親商品のSKUマッピングを自動保存
        if parent_data.get('rakuten_sku'):
            self.save_sku_mapping(
                management_number=parent_data['product_code'],
                rakuten_sku=parent_data['rakuten_sku'],
                choice_code=parent_data.get('choice_code', ''),
                notes=f"Auto-saved parent item from order {order_number}"
            )
        
        saved_count += 1
        
        # selectedItemsから子商品情報を抽出
        selected_items = parent_item.get("selectedItems", [])
        for child_item in selected_items:
            # 子商品の数量は親商品と同じ
            child_item["units"] = parent_item.get("units", 0)
            # 価格は親商品の価格を継承（または0）
            if "price" not in child_item:
                child_item["price"] = 0
            
            # _prepare_item_dataを使用して子商品データを準備
            child_item_data = self._prepare_item_data(
                child_item, 
                order_id, 
                is_parent=False, 
                is_child=True, 
                parent_product_code=parent_data['product_code']
            )
            
            # 子商品データの保存
            child_result = Database.get_client().table("order_items").insert(child_item_data).execute()
            
            if not child_result.data:
                raise Exception(f"子商品の保存に失敗: {child_item_data['product_code']}")
            
            logger.info(f"子商品 {child_item_data['product_code']} を保存しました (注文: {order_number})")
            
            # 子商品のSKUマッピングを自動保存
            if child_item_data.get('rakuten_sku'):
                self.save_sku_mapping(
                    management_number=child_item_data['product_code'],
                    rakuten_sku=child_item_data['rakuten_sku'],
                    choice_code=child_item_data.get('choice_code', ''),
                    notes=f"Auto-saved child item from order {order_number}"
                )
            
            saved_count += 1
        
        return saved_count

    def _get_platform_id_with_retry(self, max_retries=3, delay=1):
        """Platform IDの取得（リトライ機能付き）"""
        supabase = Database.get_client()
        if not supabase:
            raise ValueError("Supabaseクライアントが初期化されていません")
        
        for attempt in range(max_retries):
            try:
                response = Database.get_client().table("platform").select("id").eq("platform_code", "rakuten").execute()
                if response.data:
                    return response
                raise ValueError("プラットフォーム 'rakuten' が見つかりません")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)

    def get_item_detail(self, item_url: str) -> Dict[str, Any]:
        """商品詳細情報をURLから取得"""
        url = f'{self.base_url}/items/get'
        
        # URLから商品IDを抽出
        import re
        match = re.search(r'/([^/]+)/$', item_url)
        if not match:
            raise ValueError(f"商品URLから商品IDを抽出できません: {item_url}")
        
        item_id = match.group(1)
        
        request_data = {
            "itemId": item_id
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
                    raise HTTPException(status_code=401, detail="認証に失敗しました")
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"商品詳細取得エラー: {str(e)}")
            raise

    def get_rakuten_sku_info(self, management_number: str) -> Dict[str, Any]:
        """管理商品番号から楽天SKU情報を取得"""
        url = f'{self.base_url}/items/search'
        
        search_data = {
            "searchType": 1,  # 商品管理番号で検索
            "searchValue": management_number,
            "PaginationRequestModel": {
                "requestRecordsAmount": 100,
                "requestPage": 1
            }
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    url,
                    headers=self.headers,
                    json=search_data,
                    timeout=30.0
                )
                
                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail="認証に失敗しました")
                
                response.raise_for_status()
                data = response.json()
                
                # 商品情報から実際のSKUを抽出
                items = data.get('ItemModelList', [])
                sku_info = {}
                
                for item in items:
                    # 楽天の実際のSKU情報を抽出
                    sku_models = item.get('SkuModelList', [])
                    for sku in sku_models:
                        sku_id = sku.get('skuId')  # 実際の楽天SKU
                        variant_id = sku.get('variantId')
                        merchant_sku = sku.get('merchantDefinedSkuId')
                        
                        if sku_id:
                            sku_info[str(sku_id)] = {
                                'variant_id': variant_id,
                                'merchant_sku': merchant_sku,
                                'item_name': item.get('itemName', ''),
                                'item_number': item.get('itemNumber', ''),
                                'sku_info': sku.get('skuInfo', {})
                            }
                
                return {
                    'management_number': management_number,
                    'total_skus': len(sku_info),
                    'sku_details': sku_info,
                    'raw_data': data
                }
                
        except Exception as e:
            logger.error(f"楽天SKU情報取得エラー: {str(e)}")
            raise

    def save_sku_mapping(self, management_number: str, rakuten_sku: str, choice_code: str = "", notes: str = "") -> bool:
        """楽天SKUマッピング情報をデータベースに保存"""
        try:
            if not supabase:
                raise ValueError("Supabaseクライアントが初期化されていません")
            
            # 共通商品コードを生成（例：CM + 管理番号末尾3桁 + 選択肢コード）
            common_code_base = f"CM{management_number[-3:]}"
            if choice_code:
                common_product_code = f"{common_code_base}_{choice_code}"
            else:
                common_product_code = common_code_base
            
            mapping_data = {
                "rakuten_product_code": management_number,
                "rakuten_sku": rakuten_sku,
                "rakuten_choice_code": choice_code,
                "common_product_code": common_product_code,
                "mapping_confidence": 90,  # 自動生成は90%
                "mapping_type": "auto",
                "notes": notes or f"Auto-generated from order sync at {datetime.now(timezone.utc).isoformat()}",
                "created_by": "system_auto_sync"
            }
            
            # 重複チェック
            existing = Database.get_client().table("product_mapping_rakuten").select("id").eq("rakuten_product_code", management_number).eq("rakuten_choice_code", choice_code or "").execute()
            
            if existing.data:
                # 既存レコードを更新
                result = Database.get_client().table("product_mapping_rakuten").update(mapping_data).eq("rakuten_product_code", management_number).eq("rakuten_choice_code", choice_code or "").execute()
            else:
                # 新規レコードを挿入
                result = Database.get_client().table("product_mapping_rakuten").insert(mapping_data).execute()
            
            if result.data:
                logger.info(f"SKUマッピング保存成功: {management_number} -> {rakuten_sku} -> {common_product_code}")
                return True
            else:
                logger.error(f"SKUマッピング保存失敗: {management_number}")
                return False
                
        except Exception as e:
            logger.error(f"SKUマッピング保存エラー: {str(e)}")
            return False