#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在庫管理モジュール
在庫の更新と売上集計処理
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from core.database import supabase

logger = logging.getLogger(__name__)

def get_platform_id(platform_code: str) -> Optional[int]:
    """プラットフォームコードからIDを取得"""
    try:
        platform_result = supabase.table("platform").select("id").eq("platform_code", platform_code).execute()
        if platform_result.data:
            return platform_result.data[0]["id"]
        return None
    except Exception as e:
        logger.error(f"プラットフォームID取得エラー: {str(e)}")
        return None

def update_inventory(product_code: str, quantity: int, movement_type: str, 
                          reference_id: int, platform_id: int, notes: str = "") -> bool:
    """在庫を更新し、在庫変動を記録する（全プラットフォーム共通）"""
    try:
        # 商品が在庫テーブルに存在するか確認
        inventory_result = supabase.table("inventory").select("*").eq(
            "product_code", product_code
        ).eq("platform_id", platform_id).execute()
        
        if not inventory_result.data:
            logger.warning(f"商品 {product_code} (プラットフォームID: {platform_id}) は在庫テーブルに存在しません。スキップします。")
            return False
        
        # 1. 在庫変動を記録
        movement_data = {
            "product_code": product_code,
            "platform_id": platform_id,
            "quantity": quantity,
            "movement_type": movement_type,
            "reference_id": reference_id,
            "notes": notes,
            "movement_date": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        movement_result = supabase.table("stock_movements").insert(movement_data).execute()
        
        # 2. 在庫テーブルの更新
        current_stock = inventory_result.data[0]["current_stock"]
        new_stock = current_stock + quantity
        
        update_result = supabase.table("inventory").update({
            "current_stock": new_stock,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", inventory_result.data[0]["id"]).execute()
        
        return True
    
    except Exception as e:
        logger.error(f"在庫更新エラー ({product_code}): {str(e)}")
        raise

class RakutenConnector:
    """楽天用在庫管理コネクタ"""
    
    def __init__(self):
        self.platform_code = "rakuten"
        self.platform_id = None
    
    def initialize(self) -> int:
        """プラットフォームIDを初期化"""
        self.platform_id = get_platform_id(self.platform_code)
        if not self.platform_id:
            raise ValueError(f"プラットフォーム '{self.platform_code}' が見つかりません")
        return self.platform_id
    
    def extract_inventory_items(self, days: Optional[int] = None) -> Dict[str, Any]:
        """楽天の注文データから在庫管理用の商品を抽出"""
        self.initialize()
        
        try:
            # 注文データ取得期間を設定（指定がなければすべて）
            query = supabase.table("order_items").select(
                "product_code", "product_name", "merchant_item_id", 
                "item_number", "variant_id", "is_parent", "is_child"
            )
            
            if days:
                start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                # order_idから対応する注文日時が一定期間内のものだけを取得
                orders = supabase.table("orders").select("id").gte("order_date", start_date).execute()
                order_ids = [order["id"] for order in orders.data]
                if order_ids:
                    query = query.in_("order_id", order_ids)
            
            items_result = query.execute()
            
            if not items_result.data:
                return {"message": "抽出可能な商品がありません"}
            
            # 在庫管理対象の商品を格納するリスト
            inventory_items = []
            unique_product_codes = set()
            
            for item in items_result.data:
                product_code = item.get("product_code")
                
                # 親商品は除外し、通常商品または子商品のみを対象とする
                if (not item.get("is_parent", False)) and product_code and product_code not in unique_product_codes:
                    inventory_items.append({
                        "product_code": product_code,
                        "product_name": item.get("product_name", ""),
                        "platform_id": self.platform_id,
                        "platform_product_id": product_code,  # 楽天の場合は同じ
                        "merchant_item_id": item.get("merchant_item_id", ""),
                        "item_number": item.get("item_number", ""),
                        "variant_id": item.get("variant_id", ""),
                        "is_active": True
                    })
                    unique_product_codes.add(product_code)
            
            # チョイス商品の選択肢も抽出
            items_with_choices = supabase.table("order_items").select(
                "item_choice"
            ).neq("item_choice", None).execute()
            
            for item in items_with_choices.data:
                item_choice = item.get("item_choice")
                if item_choice:
                    try:
                        choices = json.loads(item_choice)
                        for choice in choices:
                            if "code" in choice and choice["code"] and choice["code"] not in unique_product_codes:
                                inventory_items.append({
                                    "product_code": choice["code"],
                                    "product_name": choice.get("name", ""),
                                    "platform_id": self.platform_id,
                                    "platform_product_id": choice["code"],
                                    "merchant_item_id": "",
                                    "item_number": "",
                                    "variant_id": "",
                                    "is_active": True
                                })
                                unique_product_codes.add(choice["code"])
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            return {
                "total_items": len(inventory_items),
                "inventory_items": inventory_items
            }
        
        except Exception as e:
            logger.error(f"楽天商品抽出エラー: {str(e)}")
            raise
    
    def process_order_inventory(self, order_id: int) -> Dict[str, Any]:
        """楽天注文の在庫減少処理"""
        self.initialize()
        
        try:
            # 注文商品を取得
            items_result = supabase.table("order_items").select("*").eq("order_id", order_id).execute()
            
            processed_items = []
            
            for item in items_result.data:
                product_code = item["product_code"]
                quantity = item["quantity"]
                
                # 親商品は除外し、通常商品と子商品のみを処理
                if not item.get("is_parent", False):
                    # 在庫を減少
                    update_inventory(
                        product_code, 
                        -quantity, 
                        "order", 
                        order_id, 
                        self.platform_id
                    )
                    processed_items.append({
                        "product_code": product_code,
                        "quantity": quantity,
                        "type": "通常商品" if not item.get("is_child", False) else "子商品"
                    })
                
                # チョイス商品の選択肢があれば処理
                if item.get("item_choice"):
                    try:
                        choices = json.loads(item["item_choice"])
                        for choice in choices:
                            if "code" in choice and choice["code"]:
                                # 選択された子商品の在庫を減少
                                update_inventory(
                                    choice["code"], 
                                    -quantity, 
                                    "order", 
                                    order_id, 
                                    self.platform_id,
                                    notes=f"チョイス商品の選択肢：{choice.get('name', '')}"
                                )
                                processed_items.append({
                                    "product_code": choice["code"],
                                    "quantity": quantity,
                                    "type": "チョイス商品選択肢"
                                })
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"選択肢データの解析に失敗: {item.get('item_choice')}")
                        continue
            
            return {
                "success": True,
                "order_id": order_id,
                "platform": self.platform_code,
                "processed_items": processed_items
            }
        
        except Exception as e:
            logger.error(f"楽天在庫処理エラー: {str(e)}")
            raise
    
    def update_sales_data(self, days: int = 7) -> Dict[str, Any]:
        """楽天の売上データを更新する"""
        self.initialize()
        
        try:
            # 期間指定
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # 注文データを取得
            orders_result = supabase.table("orders").select("*").gte(
                "order_date", start_date.isoformat()
            ).lte("order_date", end_date.isoformat()).execute()
            
            if not orders_result.data:
                return {"message": "対象期間の注文データがありません"}
            
            # 処理済み注文のカウント
            processed_count = 0
            sales_data = {}  # 日付・商品別の売上データ
            
            for order in orders_result.data:
                order_id = order["id"]
                order_date_str = order.get("order_date")
                
                if not order_date_str:
                    continue
                    
                # 注文日をDateオブジェクトに変換
                try:
                    order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00')).date()
                except ValueError:
                    logger.warning(f"日付形式が無効: {order_date_str}")
                    continue
                
                # 注文商品を取得
                items_result = supabase.table("order_items").select("*").eq("order_id", order_id).execute()
                
                for item in items_result.data:
                    # 親商品は除外
                    if item.get("is_parent", False):
                        continue
                    
                    product_code = item["product_code"]
                    product_name = item.get("product_name", "")
                    quantity = item.get("quantity", 0)
                    unit_price = item.get("unit_price", 0)
                    
                    # 売上を計算
                    sales_amount = unit_price * quantity
                    
                    # 日付・商品ごとに集計
                    key = (order_date.isoformat(), product_code)
                    if key not in sales_data:
                        sales_data[key] = {
                            "date": order_date.isoformat(),
                            "product_code": product_code,
                            "product_name": product_name,
                            "platform_id": self.platform_id,
                            "units": 0,
                            "sales": 0
                        }
                    
                    sales_data[key]["units"] += quantity
                    sales_data[key]["sales"] += sales_amount
                
                # チョイス商品の選択肢も処理
                for item in items_result.data:
                    item_choice = item.get("item_choice")
                    if item_choice:
                        try:
                            choices = json.loads(item_choice)
                            quantity = item.get("quantity", 0)
                            # チョイス商品は単価0円で集計（数量のみ）
                            for choice in choices:
                                if "code" in choice and choice["code"]:
                                    key = (order_date.isoformat(), choice["code"])
                                    if key not in sales_data:
                                        sales_data[key] = {
                                            "date": order_date.isoformat(),
                                            "product_code": choice["code"],
                                            "product_name": choice.get("name", ""),
                                            "platform_id": self.platform_id,
                                            "units": 0,
                                            "sales": 0  # チョイス商品単体の売上は0円
                                        }
                                    
                                    sales_data[key]["units"] += quantity
                        except (json.JSONDecodeError, TypeError):
                            continue
                
                processed_count += 1
            
            # 集計データをsales_dailyテーブルに保存
            inserted_count = 0
            updated_count = 0
            
            for key, data in sales_data.items():
                # 既存データを検索
                existing = supabase.table("sales_daily").select("*").eq(
                    "summary_date", data["date"]
                ).eq("product_code", data["product_code"]).eq(
                    "platform_id", data["platform_id"]
                ).execute()
                
                if existing.data:
                    # 既存データを更新
                    supabase.table("sales_daily").update({
                        "units_sold": data["units"],
                        "gross_sales": data["sales"],
                        "net_sales": data["sales"],
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", existing.data[0]["id"]).execute()
                    updated_count += 1
                else:
                    # 新規データを挿入
                    supabase.table("sales_daily").insert({
                        "summary_date": data["date"],
                        "product_code": data["product_code"],
                        "product_name": data["product_name"],
                        "platform_id": data["platform_id"],
                        "units_sold": data["units"],
                        "gross_sales": data["sales"],
                        "discounts": 0,
                        "net_sales": data["sales"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).execute()
                    inserted_count += 1
            
            return {
                "message": "売上データを更新しました",
                "platform": self.platform_code,
                "processed_orders": processed_count,
                "total_products": len(sales_data),
                "inserted": inserted_count,
                "updated": updated_count
            }
            
        except Exception as e:
            logger.error(f"楽天売上更新エラー: {str(e)}")
            raise