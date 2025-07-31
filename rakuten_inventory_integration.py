#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天在庫連動システム
楽天注文 → 共通コード変換 → 在庫自動減算
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import logging

from core.database import supabase

logger = logging.getLogger(__name__)

class RakutenInventoryIntegration:
    """楽天在庫連動システム"""
    
    def __init__(self):
        if not supabase:
            raise Exception("Supabase client not initialized")
        self.client = supabase
    
    def map_rakuten_to_common_code(self, rakuten_product_code: str) -> Optional[Tuple[str, str]]:
        """
        楽天商品コードを共通コードにマッピング
        
        Args:
            rakuten_product_code: 楽天商品番号（例: 10000059）
            
        Returns:
            Tuple[common_code, product_name] または None
        """
        try:
            # 1. product_masterテーブルで楽天SKUとして検索
            master_result = self.client.table('product_master').select(
                'common_code, product_name'
            ).eq('rakuten_sku', rakuten_product_code).execute()
            
            if master_result.data:
                item = master_result.data[0]
                return item['common_code'], item['product_name']
            
            # 2. choice_code_mappingテーブルで楽天SKUとして検索
            choice_result = self.client.table('choice_code_mapping').select(
                'common_code, product_name'
            ).eq('rakuten_sku', rakuten_product_code).execute()
            
            if choice_result.data:
                item = choice_result.data[0]
                return item['common_code'], item['product_name']
            
            # 3. 楽天商品番号の親商品を探す（選択肢商品の場合）
            # 例: 10000059-variant を 10000059 で検索
            base_code = rakuten_product_code.split('-')[0]
            if base_code != rakuten_product_code:
                return self.map_rakuten_to_common_code(base_code)
            
            logger.warning(f"楽天商品コード {rakuten_product_code} の共通コードが見つかりません")
            return None
            
        except Exception as e:
            logger.error(f"商品コードマッピングエラー: {str(e)}")
            return None
    
    def get_current_stock(self, common_code: str) -> int:
        """共通コードの現在在庫を取得"""
        try:
            inventory_result = self.client.table('inventory').select(
                'current_stock'
            ).eq('common_code', common_code).execute()
            
            if inventory_result.data:
                return inventory_result.data[0]['current_stock']
            else:
                # 在庫レコードが存在しない場合は0を返す
                logger.warning(f"共通コード {common_code} の在庫レコードが見つかりません")
                return 0
                
        except Exception as e:
            logger.error(f"在庫取得エラー: {str(e)}")
            return 0
    
    def update_stock(self, common_code: str, quantity_change: int, reason: str) -> bool:
        """
        在庫を更新
        
        Args:
            common_code: 共通コード
            quantity_change: 在庫変更量（負の値で減算）
            reason: 変更理由
            
        Returns:
            成功時True
        """
        try:
            # 現在在庫を取得
            current_stock = self.get_current_stock(common_code)
            new_stock = current_stock + quantity_change
            
            # 在庫がマイナスになる場合の警告
            if new_stock < 0:
                logger.warning(f"在庫不足: {common_code} の在庫が {new_stock} になります")
            
            # 在庫テーブルの更新または作成
            inventory_check = self.client.table('inventory').select('id').eq('common_code', common_code).execute()
            
            if inventory_check.data:
                # 既存レコードを更新
                update_result = self.client.table('inventory').update({
                    'current_stock': new_stock,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).eq('common_code', common_code).execute()
                
                if update_result.data:
                    logger.info(f"在庫更新: {common_code} {current_stock} → {new_stock} ({reason})")
                    return True
            else:
                # 商品マスターから商品名を取得
                product_result = self.client.table('product_master').select('product_name').eq('common_code', common_code).execute()
                product_name = product_result.data[0]['product_name'] if product_result.data else f"商品 {common_code}"
                
                # 新規在庫レコードを作成
                insert_result = self.client.table('inventory').insert({
                    'common_code': common_code,
                    'product_name': product_name,
                    'current_stock': new_stock,
                    'minimum_stock': 10,
                    'reorder_point': 20,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).execute()
                
                if insert_result.data:
                    logger.info(f"在庫新規作成: {common_code} = {new_stock} ({reason})")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"在庫更新エラー: {str(e)}")
            return False
    
    def process_order_inventory_impact(self, order_id: int) -> Dict:
        """
        注文による在庫への影響を処理
        
        Args:
            order_id: 注文ID
            
        Returns:
            処理結果の辞書
        """
        try:
            # 注文商品を取得
            order_items = self.client.table('order_items').select(
                'product_code, product_name, quantity'
            ).eq('order_id', order_id).execute()
            
            if not order_items.data:
                return {
                    "status": "no_items",
                    "message": "注文に商品が見つかりません",
                    "order_id": order_id
                }
            
            processed_items = []
            total_items = len(order_items.data)
            successful_items = 0
            
            for item in order_items.data:
                rakuten_code = item['product_code']
                quantity = item['quantity']
                product_name = item['product_name']
                
                # 楽天商品コードを共通コードに変換
                mapping_result = self.map_rakuten_to_common_code(rakuten_code)
                
                if mapping_result:
                    common_code, mapped_name = mapping_result
                    
                    # 在庫を減算
                    stock_updated = self.update_stock(
                        common_code, 
                        -quantity,  # 負の値で減算
                        f"楽天注文 {order_id} による出庫"
                    )
                    
                    if stock_updated:
                        successful_items += 1
                        status = "success"
                        current_stock = self.get_current_stock(common_code)
                    else:
                        status = "stock_update_failed"
                        current_stock = None
                    
                    processed_items.append({
                        "rakuten_code": rakuten_code,
                        "common_code": common_code,
                        "product_name": product_name,
                        "mapped_name": mapped_name,
                        "quantity_sold": quantity,
                        "current_stock": current_stock,
                        "status": status
                    })
                else:
                    # 共通コードが見つからない場合
                    processed_items.append({
                        "rakuten_code": rakuten_code,
                        "product_name": product_name,
                        "quantity_sold": quantity,
                        "status": "mapping_not_found",
                        "message": "共通コードが見つかりません"
                    })
            
            return {
                "status": "success",
                "order_id": order_id,
                "summary": {
                    "total_items": total_items,
                    "successful_items": successful_items,
                    "failed_items": total_items - successful_items,
                    "success_rate": f"{(successful_items/total_items*100):.1f}%"
                },
                "processed_items": processed_items
            }
            
        except Exception as e:
            logger.error(f"注文在庫処理エラー: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "order_id": order_id
            }
    
    def get_inventory_status(self) -> Dict:
        """現在の在庫状況を取得"""
        try:
            inventory_result = self.client.table('inventory').select(
                'common_code, product_name, current_stock, minimum_stock, reorder_point, last_updated'
            ).order('current_stock').execute()
            
            if not inventory_result.data:
                return {
                    "status": "no_data",
                    "message": "在庫データがありません"
                }
            
            # 在庫状況の分析
            total_products = len(inventory_result.data)
            out_of_stock = [item for item in inventory_result.data if item['current_stock'] <= 0]
            low_stock = [item for item in inventory_result.data if 0 < item['current_stock'] <= item.get('reorder_point', 20)]
            adequate_stock = [item for item in inventory_result.data if item['current_stock'] > item.get('reorder_point', 20)]
            
            return {
                "status": "success",
                "summary": {
                    "total_products": total_products,
                    "out_of_stock": len(out_of_stock),
                    "low_stock": len(low_stock),
                    "adequate_stock": len(adequate_stock)
                },
                "out_of_stock_items": out_of_stock[:10],  # 上位10件
                "low_stock_items": low_stock[:10],  # 上位10件
                "all_inventory": inventory_result.data
            }
            
        except Exception as e:
            logger.error(f"在庫状況取得エラー: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def initialize_inventory_from_product_master(self, initial_stock: int = 100) -> Dict:
        """商品マスターから在庫データを初期化"""
        try:
            # 商品マスターから全商品を取得
            products = self.client.table('product_master').select(
                'common_code, product_name, product_type'
            ).eq('is_active', True).execute()
            
            if not products.data:
                return {
                    "status": "no_data",
                    "message": "商品マスターにデータがありません"
                }
            
            created_count = 0
            updated_count = 0
            
            for product in products.data:
                common_code = product['common_code']
                product_name = product['product_name']
                
                # 既存在庫をチェック
                existing = self.client.table('inventory').select('id').eq('common_code', common_code).execute()
                
                inventory_data = {
                    'common_code': common_code,
                    'product_name': product_name,
                    'current_stock': initial_stock,
                    'minimum_stock': 10,
                    'reorder_point': 20,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
                
                if existing.data:
                    # 既存レコードを更新
                    self.client.table('inventory').update(inventory_data).eq('common_code', common_code).execute()
                    updated_count += 1
                else:
                    # 新規作成
                    inventory_data['created_at'] = datetime.now(timezone.utc).isoformat()
                    self.client.table('inventory').insert(inventory_data).execute()
                    created_count += 1
            
            return {
                "status": "success",
                "message": "在庫データを初期化しました",
                "summary": {
                    "total_products": len(products.data),
                    "created": created_count,
                    "updated": updated_count,
                    "initial_stock_per_item": initial_stock
                }
            }
            
        except Exception as e:
            logger.error(f"在庫初期化エラー: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }


def add_inventory_integration_endpoints(app, inventory_integration: RakutenInventoryIntegration):
    """在庫連動エンドポイントを追加"""
    
    @app.post("/inventory/initialize-from-master")
    async def initialize_inventory_from_master(initial_stock: int = 100):
        """商品マスターから在庫を初期化"""
        return inventory_integration.initialize_inventory_from_product_master(initial_stock)
    
    @app.get("/inventory/status")
    async def get_inventory_status():
        """現在の在庫状況を取得"""
        return inventory_integration.get_inventory_status()
    
    @app.post("/inventory/process-order/{order_id}")
    async def process_order_inventory(order_id: int):
        """注文による在庫影響を処理"""
        return inventory_integration.process_order_inventory_impact(order_id)
    
    @app.get("/inventory/mapping-test/{rakuten_code}")
    async def test_rakuten_mapping(rakuten_code: str):
        """楽天商品コードのマッピングテスト"""
        mapping_result = inventory_integration.map_rakuten_to_common_code(rakuten_code)
        
        if mapping_result:
            common_code, product_name = mapping_result
            current_stock = inventory_integration.get_current_stock(common_code)
            
            return {
                "status": "success",
                "rakuten_code": rakuten_code,
                "common_code": common_code,
                "product_name": product_name,
                "current_stock": current_stock
            }
        else:
            return {
                "status": "not_found",
                "rakuten_code": rakuten_code,
                "message": "共通コードが見つかりません"
            }