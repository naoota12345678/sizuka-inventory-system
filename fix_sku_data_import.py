#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天APIから正しいSKUデータを取り込み直す
"""

import logging
from supabase import create_client
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class SKUDataFixer:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
    def extract_sku_from_extended_data(self, order_item):
        """extended_rakuten_dataからSKU情報を抽出"""
        extended_data = order_item.get('extended_rakuten_data', {})
        if not extended_data:
            return None
            
        # raw_sku_dataから抽出
        raw_sku_data = extended_data.get('raw_sku_data', {})
        if raw_sku_data:
            # original_sku_infoから最初のSKUを取得
            original_sku_info = raw_sku_data.get('original_sku_info', [])
            if original_sku_info and len(original_sku_info) > 0:
                sku_info = original_sku_info[0]
                
                # skuIdが優先
                if sku_info.get('skuId'):
                    return str(sku_info.get('skuId'))
                # variantIdを次に試す
                elif sku_info.get('variantId'):
                    return str(sku_info.get('variantId'))
                # merchantDefinedSkuIdも確認
                elif sku_info.get('merchantDefinedSkuId'):
                    return str(sku_info.get('merchantDefinedSkuId'))
        
        return None
    
    def fix_rakuten_item_number_fields(self):
        """order_itemsテーブルのrakuten_item_numberフィールドを修正"""
        logger.info("=== rakuten_item_numberフィールドの修正 ===")
        
        # rakuten_item_numberがNullの商品を取得
        orders = self.supabase.table("order_items").select("*").is_("rakuten_item_number", "null").not_.like("product_code", "TEST%").limit(100).execute()
        
        logger.info(f"修正対象: {len(orders.data)}件")
        
        updated_count = 0
        failed_count = 0
        
        for order in orders.data:
            try:
                # extended_rakuten_dataからSKUを抽出
                extracted_sku = self.extract_sku_from_extended_data(order)
                
                if extracted_sku:
                    # rakuten_item_numberフィールドを更新
                    update_result = self.supabase.table("order_items").update({
                        "rakuten_item_number": extracted_sku
                    }).eq("id", order["id"]).execute()
                    
                    if update_result.data:
                        logger.info(f"✓ 更新成功: ID {order['id']} → rakuten_item_number: {extracted_sku}")
                        updated_count += 1
                    else:
                        logger.error(f"✗ 更新失敗: ID {order['id']}")
                        failed_count += 1
                else:
                    logger.warning(f"SKU抽出失敗: ID {order['id']} product_code: {order.get('product_code')}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"エラー: ID {order['id']} - {str(e)}")
                failed_count += 1
        
        logger.info(f"\n=== 修正結果 ===")
        logger.info(f"更新成功: {updated_count}件")
        logger.info(f"失敗: {failed_count}件")
        
        return updated_count, failed_count
    
    def test_sku_extraction(self):
        """SKU抽出のテスト"""
        logger.info("=== SKU抽出テスト ===")
        
        # サンプルデータを取得
        orders = self.supabase.table("order_items").select("*").not_.like("product_code", "TEST%").limit(5).execute()
        
        for order in orders.data:
            logger.info(f"\n商品ID: {order['id']}")
            logger.info(f"product_code: {order.get('product_code')}")
            logger.info(f"現在のrakuten_item_number: {order.get('rakuten_item_number')}")
            
            # SKU抽出を試行
            extracted_sku = self.extract_sku_from_extended_data(order)
            logger.info(f"抽出されたSKU: {extracted_sku}")
            
            # extended_rakuten_dataの構造確認
            extended_data = order.get('extended_rakuten_data', {})
            if extended_data:
                raw_sku_data = extended_data.get('raw_sku_data', {})
                if raw_sku_data:
                    logger.info(f"raw_sku_data構造: {list(raw_sku_data.keys())}")
                    original_sku_info = raw_sku_data.get('original_sku_info', [])
                    if original_sku_info:
                        logger.info(f"original_sku_info[0]: {original_sku_info[0] if len(original_sku_info) > 0 else 'None'}")

def main():
    fixer = SKUDataFixer()
    
    # まずテストを実行
    print("=== SKU抽出テスト実行 ===")
    fixer.test_sku_extraction()
    
    # ユーザー確認
    response = input("\nrakuten_item_numberフィールドを修正しますか？ (y/n): ")
    if response.lower() == 'y':
        updated, failed = fixer.fix_rakuten_item_number_fields()
        print(f"\n修正完了: 成功 {updated}件, 失敗 {failed}件")
    else:
        print("修正をキャンセルしました")

if __name__ == "__main__":
    main()