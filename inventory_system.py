#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天在庫連動システム
Rakuten Inventory Integration System
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

from core.database import supabase

logger = logging.getLogger(__name__)

class RakutenInventorySystem:
    """楽天在庫連動システム"""
    
    def __init__(self):
        if not supabase:
            raise Exception("Supabase client not initialized")
        self.client = supabase
        
        # 楽天プラットフォームIDを取得
        try:
            platform_result = self.client.table('platform').select('id').eq('platform_code', 'rakuten').execute()
            if platform_result.data:
                self.rakuten_platform_id = platform_result.data[0]['id']
            else:
                raise Exception("楽天プラットフォームが見つかりません")
        except Exception as e:
            logger.error(f"プラットフォーム情報の取得に失敗: {str(e)}")
            raise
    
    def create_inventory_from_orders(self, initial_stock: int = 100) -> Dict:
        """注文データから在庫データを自動作成"""
        try:
            # 既存のテーブル構造を利用して在庫管理を行う
            # unified_productsテーブルを在庫管理として活用
            
            # 楽天注文商品から商品一覧を抽出
            order_items = self.client.table('order_items').select(
                'product_code, product_name'
            ).execute()
            
            if not order_items.data:
                return {"status": "no_data", "message": "注文商品データが見つかりません"}
            
            # 商品コードごとにユニーク化
            unique_products = {}
            for item in order_items.data:
                code = item['product_code']
                name = item['product_name']
                
                if code not in unique_products:
                    unique_products[code] = {
                        'product_code': code,
                        'product_name': name,
                        'total_orders': 0,
                        'total_quantity': 0
                    }
                unique_products[code]['total_orders'] += 1
            
            # 各商品の販売数量を計算
            for code in unique_products.keys():
                qty_result = self.client.table('order_items').select('quantity').eq('product_code', code).execute()
                if qty_result.data:
                    total_qty = sum(item['quantity'] for item in qty_result.data)
                    unique_products[code]['total_quantity'] = total_qty
            
            # unified_productsテーブルに商品マスターとして登録
            new_products = []
            updated_count = 0
            
            for code, data in unique_products.items():
                try:
                    # 既存商品をチェック
                    existing = self.client.table('unified_products').select('id').eq('sku', code).execute()
                    
                    product_data = {
                        'sku': code,
                        'name': data['product_name'],
                        'category': '楽天商品',
                        'cost': 0,  # コストは後で設定
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    if existing.data:
                        # 既存商品を更新
                        self.client.table('unified_products').update(product_data).eq('sku', code).execute()
                        updated_count += 1
                    else:
                        # 新規商品として追加
                        new_products.append(product_data)
                        
                except Exception as e:
                    logger.error(f"商品 {code} の処理でエラー: {str(e)}")
                    continue
            
            # 新規商品の一括登録
            created_count = 0
            if new_products:
                try:
                    # バッチ処理で登録
                    batch_size = 10
                    for i in range(0, len(new_products), batch_size):
                        batch = new_products[i:i+batch_size]
                        result = self.client.table('unified_products').insert(batch).execute()
                        if result.data:
                            created_count += len(result.data)
                        
                except Exception as e:
                    logger.error(f"商品の一括登録でエラー: {str(e)}")
            
            # inventory_transactionsテーブルに初期在庫を記録
            self._create_initial_inventory_transactions()
            
            return {
                "status": "success",
                "message": "楽天商品データから在庫システムを初期化しました",
                "summary": {
                    "total_unique_products": len(unique_products),
                    "new_products_created": created_count,
                    "existing_products_updated": updated_count,
                    "initial_stock_per_item": initial_stock
                },
                "products": list(unique_products.values())[:10]  # サンプル10件
            }
            
        except Exception as e:
            logger.error(f"在庫システム初期化エラー: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _create_initial_inventory_transactions(self):
        """初期在庫取引を記録"""
        try:
            # 作成された商品に対して初期在庫取引を記録
            products = self.client.table('unified_products').select('id, sku, name').execute()
            
            if products.data:
                transactions = []
                for product in products.data:
                    transactions.append({
                        'product_id': product['id'],
                        'transaction_type': 'initial_stock',
                        'quantity': 100,  # 初期在庫数
                        'notes': f'楽天商品 {product["sku"]} の初期在庫設定',
                        'created_at': datetime.now(timezone.utc).isoformat()
                    })
                
                # バッチ処理で取引履歴を記録
                if transactions:
                    batch_size = 20
                    for i in range(0, len(transactions), batch_size):
                        batch = transactions[i:i+batch_size]
                        self.client.table('inventory_transactions').insert(batch).execute()
                        
        except Exception as e:
            logger.error(f"初期在庫取引の記録でエラー: {str(e)}")
    
    def process_order_inventory_impact(self, order_id: int) -> Dict:
        """注文による在庫への影響を処理"""
        try:
            # 注文の商品を取得
            order_items = self.client.table('order_items').select(
                'product_code, product_name, quantity'
            ).eq('order_id', order_id).execute()
            
            if not order_items.data:
                return {"status": "no_items", "message": "注文に商品が見つかりません"}
            
            processed_items = []
            
            for item in order_items.data:
                try:
                    # 商品マスターから商品IDを取得
                    product = self.client.table('unified_products').select('id').eq('sku', item['product_code']).execute()
                    
                    if product.data:
                        product_id = product.data[0]['id']
                        quantity = item['quantity']
                        
                        # 出庫取引を記録
                        transaction_data = {
                            'product_id': product_id,
                            'transaction_type': 'sale',
                            'quantity': -quantity,  # 出庫は負の値
                            'notes': f'楽天注文 (注文ID: {order_id}) による出庫',
                            'created_at': datetime.now(timezone.utc).isoformat()
                        }
                        
                        self.client.table('inventory_transactions').insert(transaction_data).execute()
                        
                        processed_items.append({
                            'product_code': item['product_code'],
                            'product_name': item['product_name'],
                            'quantity_sold': quantity,
                            'status': 'processed'
                        })
                    else:
                        processed_items.append({
                            'product_code': item['product_code'],
                            'product_name': item['product_name'],
                            'quantity_sold': item['quantity'],
                            'status': 'skipped',
                            'reason': 'product_not_found_in_master'
                        })
                        
                except Exception as e:
                    logger.error(f"商品 {item['product_code']} の在庫処理でエラー: {str(e)}")
                    processed_items.append({
                        'product_code': item['product_code'],
                        'status': 'error',
                        'error': str(e)
                    })
            
            return {
                "status": "success",
                "order_id": order_id,
                "processed_items": processed_items,
                "total_items": len(order_items.data),
                "successful_items": len([item for item in processed_items if item['status'] == 'processed'])
            }
            
        except Exception as e:
            logger.error(f"注文在庫処理エラー: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_current_inventory_status(self) -> Dict:
        """現在の在庫状況を取得"""
        try:
            # 商品マスターから全商品を取得
            products = self.client.table('unified_products').select('id, sku, name, category').execute()
            
            if not products.data:
                return {"status": "no_data", "message": "商品マスターにデータがありません"}
            
            inventory_status = []
            
            for product in products.data:
                # 各商品の在庫取引履歴から現在在庫を計算
                transactions = self.client.table('inventory_transactions').select(
                    'quantity, transaction_type'
                ).eq('product_id', product['id']).execute()
                
                current_stock = 0
                if transactions.data:
                    current_stock = sum(t['quantity'] for t in transactions.data)
                
                # 売上数量を計算
                sales_qty = 0
                sales_result = self.client.table('order_items').select('quantity').eq('product_code', product['sku']).execute()
                if sales_result.data:
                    sales_qty = sum(item['quantity'] for item in sales_result.data)
                
                inventory_status.append({
                    'product_code': product['sku'],
                    'product_name': product['name'],
                    'category': product['category'],
                    'current_stock': current_stock,
                    'total_sales': sales_qty,
                    'stock_status': self._get_stock_status(current_stock)
                })
            
            # 在庫状況でソート
            inventory_status.sort(key=lambda x: x['current_stock'])
            
            return {
                "status": "success",
                "total_products": len(inventory_status),
                "inventory_summary": {
                    "out_of_stock": len([item for item in inventory_status if item['current_stock'] <= 0]),
                    "low_stock": len([item for item in inventory_status if 0 < item['current_stock'] <= 10]),
                    "in_stock": len([item for item in inventory_status if item['current_stock'] > 10])
                },
                "inventory_details": inventory_status
            }
            
        except Exception as e:
            logger.error(f"在庫状況取得エラー: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _get_stock_status(self, stock: int) -> str:
        """在庫状況の判定"""
        if stock <= 0:
            return "out_of_stock"
        elif stock <= 10:
            return "low_stock"
        elif stock <= 50:
            return "medium_stock"
        else:
            return "in_stock"
    
    def get_restock_recommendations(self) -> Dict:
        """補充推奨商品の取得"""
        try:
            inventory_status = self.get_current_inventory_status()
            
            if inventory_status['status'] != 'success':
                return inventory_status
            
            # 補充が必要な商品を抽出
            need_restock = []
            
            for item in inventory_status['inventory_details']:
                if item['current_stock'] <= 10:  # 在庫10個以下
                    # 過去30日の販売ペースを計算
                    daily_sales = item['total_sales'] / 30 if item['total_sales'] > 0 else 0
                    days_remaining = item['current_stock'] / daily_sales if daily_sales > 0 else 999
                    
                    recommended_qty = max(50, int(daily_sales * 30))  # 30日分または最低50個
                    
                    need_restock.append({
                        'product_code': item['product_code'],
                        'product_name': item['product_name'],
                        'current_stock': item['current_stock'],
                        'total_sales_30days': item['total_sales'],
                        'daily_average_sales': round(daily_sales, 2),
                        'days_until_stockout': round(days_remaining, 1),
                        'recommended_restock_qty': recommended_qty,
                        'priority': 'high' if item['current_stock'] <= 0 else 'medium' if item['current_stock'] <= 5 else 'low'
                    })
            
            # 優先度でソート
            need_restock.sort(key=lambda x: (
                0 if x['priority'] == 'high' else 1 if x['priority'] == 'medium' else 2,
                x['days_until_stockout']
            ))
            
            return {
                "status": "success",
                "total_products_need_restock": len(need_restock),
                "high_priority": len([item for item in need_restock if item['priority'] == 'high']),
                "medium_priority": len([item for item in need_restock if item['priority'] == 'medium']),
                "low_priority": len([item for item in need_restock if item['priority'] == 'low']),
                "restock_recommendations": need_restock
            }
            
        except Exception as e:
            logger.error(f"補充推奨取得エラー: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }


def add_inventory_endpoints(app, inventory_system: RakutenInventorySystem):
    """在庫管理エンドポイントを追加"""
    
    @app.post("/inventory/initialize")
    async def initialize_inventory():
        """楽天商品データから在庫システムを初期化"""
        return inventory_system.create_inventory_from_orders()
    
    @app.get("/inventory/status")
    async def get_inventory_status():
        """現在の在庫状況を取得"""
        return inventory_system.get_current_inventory_status()
    
    @app.get("/inventory/restock-recommendations")
    async def get_restock_recommendations():
        """補充推奨商品を取得"""
        return inventory_system.get_restock_recommendations()
    
    @app.post("/inventory/process-order/{order_id}")
    async def process_order_inventory(order_id: int):
        """注文による在庫影響を処理"""
        return inventory_system.process_order_inventory_impact(order_id)