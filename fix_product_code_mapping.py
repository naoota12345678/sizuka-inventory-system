#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
10000XXXコードを1XXXに変換してマッピングテーブルを更新
"""

import logging
from supabase import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class ProductCodeMapper:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
    def convert_product_code(self, product_code):
        """10000XXXを1XXXに変換"""
        if product_code and product_code.startswith('10000') and len(product_code) == 8:
            # 10000XXX -> 1XXX
            return product_code[5:]  # 最後の3桁を取得
        return product_code
    
    def get_unique_product_codes(self):
        """order_itemsから一意のproduct_codeを取得"""
        result = self.supabase.table("order_items").select("product_code").not_.like("product_code", "TEST%").execute()
        
        product_codes = set()
        for item in result.data:
            code = item.get('product_code')
            if code and code.startswith('10000'):
                product_codes.add(code)
        
        return sorted(list(product_codes))
    
    def check_converted_mappings(self, product_codes):
        """変換後のコードがproduct_masterに存在するかチェック"""
        logger.info("=== 変換マッピングチェック ===")
        
        found_mappings = []
        missing_mappings = []
        
        for product_code in product_codes:
            converted_code = self.convert_product_code(product_code)
            
            # product_masterで検索
            result = self.supabase.table("product_master").select("*").eq("rakuten_sku", converted_code).execute()
            
            if result.data:
                mapping = result.data[0]
                found_mappings.append({
                    'original': product_code,
                    'converted': converted_code,
                    'common_code': mapping['common_code'],
                    'product_name': mapping.get('product_name', '')
                })
                logger.info(f"✓ {product_code} → {converted_code} → {mapping['common_code']}")
            else:
                missing_mappings.append({
                    'original': product_code,
                    'converted': converted_code
                })
                logger.warning(f"✗ {product_code} → {converted_code} (マッピングなし)")
        
        return found_mappings, missing_mappings
    
    def update_rakuten_item_numbers(self, found_mappings):
        """order_itemsのrakuten_item_numberを変換後のコードで更新"""
        logger.info("=== rakuten_item_number更新 ===")
        
        updated_count = 0
        failed_count = 0
        
        for mapping in found_mappings:
            try:
                # 該当のproduct_codeを持つ全ての注文商品を更新
                update_result = self.supabase.table("order_items").update({
                    "rakuten_item_number": mapping['converted']
                }).eq("product_code", mapping['original']).execute()
                
                if update_result.data:
                    logger.info(f"✓ 更新: {mapping['original']} → rakuten_item_number: {mapping['converted']} ({len(update_result.data)}件)")
                    updated_count += len(update_result.data)
                else:
                    logger.error(f"✗ 更新失敗: {mapping['original']}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"エラー: {mapping['original']} - {str(e)}")
                failed_count += 1
        
        logger.info(f"\n=== 更新結果 ===")
        logger.info(f"更新成功: {updated_count}件")
        logger.info(f"失敗: {failed_count}件")
        
        return updated_count, failed_count
    
    def create_missing_mappings(self, missing_mappings):
        """不足しているマッピングを自動生成"""
        logger.info("=== 不足マッピング生成 ===")
        
        created_count = 0
        failed_count = 0
        
        for missing in missing_mappings:
            try:
                # 共通コードを生成 (例: CM + 3桁番号)
                common_code = f"CM{missing['converted']}"
                
                # product_masterに新規エントリを作成
                insert_data = {
                    "rakuten_sku": missing['converted'],
                    "common_code": common_code,
                    "product_name": f"Auto-generated for {missing['original']}",
                    "product_type": "単品",
                    "created_at": "2025-08-05T00:00:00Z"
                }
                
                insert_result = self.supabase.table("product_master").insert(insert_data).execute()
                
                if insert_result.data:
                    logger.info(f"✓ 作成: {missing['converted']} → {common_code}")
                    created_count += 1
                else:
                    logger.error(f"✗ 作成失敗: {missing['converted']}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"エラー: {missing['converted']} - {str(e)}")
                failed_count += 1
        
        logger.info(f"\n=== 作成結果 ===")
        logger.info(f"作成成功: {created_count}件")
        logger.info(f"失敗: {failed_count}件")
        
        return created_count, failed_count

def main():
    mapper = ProductCodeMapper()
    
    # 1. 一意のproduct_codeを取得
    product_codes = mapper.get_unique_product_codes()
    logger.info(f"対象product_code数: {len(product_codes)}")
    
    # 2. 変換チェック
    found_mappings, missing_mappings = mapper.check_converted_mappings(product_codes)
    
    logger.info(f"\nマッピング状況:")
    logger.info(f"  発見済み: {len(found_mappings)}件")
    logger.info(f"  未発見: {len(missing_mappings)}件")
    
    # 3. 発見済みマッピングでrakuten_item_numberを更新
    if found_mappings:
        print(f"\n{len(found_mappings)}件の既存マッピングでrakuten_item_numberを更新します")
        updated, failed = mapper.update_rakuten_item_numbers(found_mappings)
    
    # 4. 不足マッピングの生成提案
    if missing_mappings:
        print(f"\n{len(missing_mappings)}件の不足マッピングが見つかりました:")
        for i, missing in enumerate(missing_mappings[:5]):
            print(f"  {missing['original']} → {missing['converted']}")
        if len(missing_mappings) > 5:
            print(f"  ... その他 {len(missing_mappings) - 5}件")
        
        response = input("\n不足マッピングを自動生成しますか？ (y/n): ")
        if response.lower() == 'y':
            created, failed = mapper.create_missing_mappings(missing_mappings)

if __name__ == "__main__":
    main()