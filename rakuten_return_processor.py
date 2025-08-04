#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rakuten Return/Refund Processing System
楽天返品・返金処理システム

既存の在庫追加ロジックを活用して返品処理を実装
安全性重視：既存システムに影響を与えず、新機能を追加
"""

from supabase import create_client
from datetime import datetime, timezone
import logging
from typing import List, Dict, Optional
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase接続情報
SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class RakutenReturnProcessor:
    """楽天返品処理システム - 既存在庫追加ロジック活用"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
    def identify_return_orders(self) -> List[Dict]:
        """
        返品・キャンセル注文を特定
        現在は全て"completed"で保存されているため、
        platform_dataから実際のステータスを確認
        """
        logger.info("=== 返品・キャンセル注文の特定 ===")
        
        try:
            # 全注文を取得（platform_dataから実際のステータスを確認）
            response = self.supabase.table("orders").select("*").limit(1000).execute()
            orders = response.data if response.data else []
            
            return_orders = []
            cancel_orders = []
            
            for order in orders:
                platform_data = order.get('platform_data', {})
                if isinstance(platform_data, dict):
                    # 楽天APIの実際のorder_progressを確認
                    order_progress = platform_data.get('orderProgress')
                    
                    if order_progress == 600:  # キャンセル
                        cancel_orders.append(order)
                        logger.info(f"キャンセル注文発見: {order['order_number']}")
                    elif order_progress == 700:  # 返品・返金
                        return_orders.append(order)
                        logger.info(f"返品注文発見: {order['order_number']}")
            
            logger.info(f"キャンセル注文: {len(cancel_orders)}件")
            logger.info(f"返品注文: {len(return_orders)}件")
            
            return {
                'returns': return_orders,
                'cancellations': cancel_orders
            }
            
        except Exception as e:
            logger.error(f"返品注文特定エラー: {str(e)}")
            return {'returns': [], 'cancellations': []}
    
    def resolve_product_to_common_code(self, rakuten_sku: str, choice_code: str = None) -> Optional[str]:
        """
        商品マッピング解決（既存ロジック活用）
        楽天SKU・選択肢コード → 共通コード
        """
        try:
            # 1. 通常商品のマッピング（product_master）
            if rakuten_sku:
                result = self.supabase.table("product_master").select("common_code").eq("rakuten_sku", rakuten_sku).execute()
                if result.data:
                    logger.debug(f"マッピング成功（通常商品）: {rakuten_sku} → {result.data[0]['common_code']}")
                    return result.data[0]['common_code']
            
            # 2. 選択肢商品のマッピング（choice_code_mapping）
            if choice_code:
                result = self.supabase.table("choice_code_mapping").select("common_code").eq("choice_info->>choice_code", choice_code).execute()
                if result.data:
                    logger.debug(f"マッピング成功（選択肢商品）: {choice_code} → {result.data[0]['common_code']}")
                    return result.data[0]['common_code']
            
            logger.warning(f"マッピング失敗: rakuten_sku={rakuten_sku}, choice_code={choice_code}")
            return None
            
        except Exception as e:
            logger.error(f"マッピング解決エラー: {str(e)}")
            return None
    
    def process_return_as_inventory_addition(self, return_item: Dict) -> bool:
        """
        返品を在庫追加として処理（既存ロジック活用）
        """
        try:
            # 商品マッピング解決
            rakuten_sku = return_item.get('rakuten_item_number', '') or return_item.get('product_code', '')
            choice_code = return_item.get('choice_code', '')
            
            common_code = self.resolve_product_to_common_code(rakuten_sku, choice_code)
            
            if not common_code:
                logger.warning(f"返品商品のマッピング失敗: {return_item.get('product_name', 'unknown')}")
                return False
            
            # 在庫トランザクション作成（既存パターン活用）
            quantity = abs(return_item.get('quantity', 1))  # 返品数量は正の値で処理
            
            transaction_data = {
                'common_code': common_code,
                'transaction_type': 'return',  # 新しいトランザクション種別
                'quantity_change': quantity,   # 正の値（在庫追加）
                'reference_order_item_id': return_item.get('id'),
                'notes': f"返品処理 - 注文番号: {return_item.get('order_number', 'unknown')}",
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # 在庫トランザクション記録
            self.supabase.table('inventory_transactions').insert(transaction_data).execute()
            
            # 在庫テーブル更新
            self.update_inventory_stock(common_code, quantity)
            
            logger.info(f"返品処理完了: {common_code} +{quantity}個")
            return True
            
        except Exception as e:
            logger.error(f"返品処理エラー: {str(e)}")
            return False
    
    def update_inventory_stock(self, common_code: str, quantity_to_add: int):
        """
        在庫数量更新（既存ロジックパターン活用）
        """
        try:
            # 現在の在庫確認
            current_inventory = self.supabase.table("inventory").select("*").eq("common_code", common_code).execute()
            
            if current_inventory.data:
                # 既存在庫更新
                current_stock = current_inventory.data[0].get('current_stock', 0)
                new_stock = current_stock + quantity_to_add
                
                self.supabase.table("inventory").update({
                    'current_stock': new_stock,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }).eq("common_code", common_code).execute()
                
                logger.info(f"在庫更新: {common_code} {current_stock} → {new_stock}")
            else:
                # 新規在庫作成（返品により初めて認識される商品）
                inventory_data = {
                    'common_code': common_code,
                    'current_stock': quantity_to_add,
                    'minimum_stock': 5,  # デフォルト値
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                self.supabase.table("inventory").insert(inventory_data).execute()
                logger.info(f"新規在庫作成: {common_code} {quantity_to_add}個")
                
        except Exception as e:
            logger.error(f"在庫更新エラー ({common_code}): {str(e)}")
    
    def process_bundle_return(self, return_item: Dict) -> bool:
        """
        まとめ商品の返品処理
        構成品に分解して個別に在庫追加
        """
        try:
            package_code = return_item.get('product_code', '')
            
            # まとめ商品の構成品取得
            components = self.supabase.table("package_components").select("*").eq("package_code", package_code).execute()
            
            if not components.data:
                # 通常商品として処理
                return self.process_return_as_inventory_addition(return_item)
            
            logger.info(f"まとめ商品の返品処理: {package_code}")
            
            success_count = 0
            return_quantity = abs(return_item.get('quantity', 1))
            
            for component in components.data:
                component_code = component.get('component_code', '')
                component_quantity = component.get('quantity', 1)
                total_component_quantity = return_quantity * component_quantity
                
                # 構成品の在庫追加
                transaction_data = {
                    'common_code': component_code,
                    'transaction_type': 'return_component',
                    'quantity_change': total_component_quantity,
                    'reference_order_item_id': return_item.get('id'),
                    'notes': f"まとめ商品返品 - パッケージ: {package_code}",
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                self.supabase.table('inventory_transactions').insert(transaction_data).execute()
                self.update_inventory_stock(component_code, total_component_quantity)
                
                success_count += 1
                logger.info(f"構成品返品完了: {component_code} +{total_component_quantity}個")
            
            logger.info(f"まとめ商品返品処理完了: {success_count}個の構成品を処理")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"まとめ商品返品処理エラー: {str(e)}")
            return False
    
    def generate_return_processing_report(self, processed_returns: List[Dict]) -> Dict:
        """
        返品処理レポート生成（CSV出力用）
        """
        try:
            report_data = []
            success_count = 0
            failed_count = 0
            total_items_returned = 0
            
            for return_result in processed_returns:
                if return_result['success']:
                    success_count += 1
                    total_items_returned += return_result.get('quantity', 0)
                else:
                    failed_count += 1
                
                report_data.append({
                    'return_date': return_result.get('return_date', ''),
                    'order_number': return_result.get('order_number', ''),
                    'product_name': return_result.get('product_name', ''),
                    'common_code': return_result.get('common_code', ''),
                    'quantity': return_result.get('quantity', 0),
                    'status': '成功' if return_result['success'] else '失敗',
                    'notes': return_result.get('notes', '')
                })
            
            summary = {
                'total_processed': len(processed_returns),
                'success_count': success_count,
                'failed_count': failed_count,
                'success_rate': (success_count / len(processed_returns) * 100) if processed_returns else 0,
                'total_items_returned': total_items_returned,
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            return {
                'summary': summary,
                'details': report_data
            }
            
        except Exception as e:
            logger.error(f"レポート生成エラー: {str(e)}")
            return {'summary': {}, 'details': []}
    
    def run_return_processing(self) -> Dict:
        """
        返品処理メイン実行
        """
        logger.info("=== 楽天返品処理開始 ===")
        
        try:
            # 1. 返品・キャンセル注文の特定
            order_data = self.identify_return_orders()
            return_orders = order_data['returns']
            
            if not return_orders:
                logger.info("処理対象の返品注文がありません")
                return {'status': 'success', 'message': '処理対象なし', 'processed': 0}
            
            # 2. 返品商品アイテムの取得
            processed_returns = []
            
            for order in return_orders:
                order_number = order['order_number']
                logger.info(f"返品注文処理開始: {order_number}")
                
                # 注文商品アイテム取得
                items_response = self.supabase.table("order_items").select("*").eq("order_number", order_number).execute()
                order_items = items_response.data if items_response.data else []
                
                for item in order_items:
                    # まとめ商品判定
                    is_bundle = self.is_bundle_product(item.get('product_code', ''))
                    
                    if is_bundle:
                        success = self.process_bundle_return(item)
                    else:
                        success = self.process_return_as_inventory_addition(item)
                    
                    processed_returns.append({
                        'success': success,
                        'return_date': order.get('order_date', ''),
                        'order_number': order_number,
                        'product_name': item.get('product_name', ''),
                        'common_code': self.resolve_product_to_common_code(
                            item.get('rakuten_item_number', ''),
                            item.get('choice_code', '')
                        ),
                        'quantity': abs(item.get('quantity', 1)),
                        'notes': '返品処理完了' if success else '処理失敗'
                    })
            
            # 3. 処理結果レポート生成
            report = self.generate_return_processing_report(processed_returns)
            
            logger.info(f"=== 返品処理完了 ===")
            logger.info(f"処理済み: {report['summary'].get('success_count', 0)}件")
            logger.info(f"失敗: {report['summary'].get('failed_count', 0)}件")
            logger.info(f"成功率: {report['summary'].get('success_rate', 0):.1f}%")
            
            return {
                'status': 'success',
                'processed': len(processed_returns),
                'report': report
            }
            
        except Exception as e:
            logger.error(f"返品処理実行エラー: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'processed': 0
            }
    
    def is_bundle_product(self, product_code: str) -> bool:
        """まとめ商品判定"""
        try:
            result = self.supabase.table("package_components").select("id").eq("package_code", product_code).limit(1).execute()
            return len(result.data) > 0
        except:
            return False

def main():
    """メイン実行関数"""
    print("=== 楽天返品処理システム ===")
    
    processor = RakutenReturnProcessor()
    
    # 返品処理実行
    result = processor.run_return_processing()
    
    if result['status'] == 'success':
        print(f"\n🎉 返品処理が完了しました！")
        print(f"処理件数: {result['processed']}件")
        
        if result.get('report'):
            summary = result['report']['summary']
            print(f"成功: {summary.get('success_count', 0)}件")
            print(f"失敗: {summary.get('failed_count', 0)}件")
            print(f"成功率: {summary.get('success_rate', 0):.1f}%")
    else:
        print(f"\n❌ エラーが発生しました: {result['message']}")

if __name__ == "__main__":
    main()