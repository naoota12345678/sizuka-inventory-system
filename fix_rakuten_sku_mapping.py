#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天SKUマッピングの修正
rakuten_item_number（1XXX形式）を使用してマッピングするように改善
"""

import logging
from supabase import create_client
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class FixedMappingSystem:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
    def extract_choice_codes(self, choice_code: str):
        """選択肢コードから個別コード（R05, C01等）を抽出"""
        if not choice_code:
            return []
        
        import re
        # パターン: 大文字英語1文字 + 数字2桁
        pattern = r'[A-Z]\d{2}'
        matches = re.findall(pattern, choice_code)
        
        # 重複を除去して順序を保持
        seen = set()
        result = []
        for match in matches:
            if match not in seen:
                seen.add(match)
                result.append(match)
        
        return result
    
    def find_choice_code_mapping(self, choice_code: str):
        """選択肢コードから共通コードを検索"""
        try:
            result = self.supabase.table("choice_code_mapping").select("*").filter("choice_info->>choice_code", "eq", choice_code).execute()
            
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"選択肢コードマッピング検索エラー: {e}")
            return None
    
    def find_product_mapping(self, order_item):
        """改善されたマッピング検索ロジック（選択肢コード対応）"""
        
        # 1. 選択肢コードがある場合の処理
        choice_code = order_item.get('choice_code', '')
        if choice_code:
            logger.debug(f"選択肢コード処理: {choice_code[:50]}...")
            
            # 選択肢コードを抽出
            choice_codes = self.extract_choice_codes(choice_code)
            if choice_codes:
                # 最初の選択肢コードでマッピング（複数ある場合は最初のもの）
                for code in choice_codes:
                    mapping = self.find_choice_code_mapping(code)
                    if mapping:
                        logger.info(f"✓ 選択肢マッピング成功: {code} → {mapping['common_code']}")
                        return mapping
                
                logger.warning(f"選択肢コードマッピング失敗: {choice_codes}")
        
        # 2. rakuten_item_numberで検索（通常商品）- 最優先
        rakuten_item_number = order_item.get('rakuten_item_number', '')
        if rakuten_item_number:
            logger.debug(f"楽天SKU {rakuten_item_number} で検索")
            
            # product_masterテーブルから検索
            result = self.supabase.table("product_master").select("*").eq("rakuten_sku", rakuten_item_number).execute()
            
            if result.data:
                logger.info(f"✓ マッピング成功: 楽天SKU {rakuten_item_number} → {result.data[0]['common_code']}")
                return result.data[0]
            else:
                # rakuten_item_numberで見つからない場合、ログに詳細記録
                logger.debug(f"rakuten_item_number {rakuten_item_number} でマッピングが見つかりません")
        
        # 2. variantIdでも検索（rakuten_item_numberと同じ値の場合が多い）
        extended_data = order_item.get('extended_rakuten_data')
        variant_id = ''
        if extended_data and isinstance(extended_data, dict):
            raw_sku_data = extended_data.get('raw_sku_data', {})
            if raw_sku_data and isinstance(raw_sku_data, dict):
                original_sku_info = raw_sku_data.get('original_sku_info', [])
                if original_sku_info and len(original_sku_info) > 0:
                    variant_id = original_sku_info[0].get('variantId', '')
        
        if variant_id and variant_id != 'normal-inventory':
            logger.debug(f"variantId {variant_id} で検索")
            
            result = self.supabase.table("product_master").select("*").eq("rakuten_sku", variant_id).execute()
            
            if result.data:
                logger.info(f"✓ マッピング成功: variantId {variant_id} → {result.data[0]['common_code']}")
                return result.data[0]
        
        # 3. 最後にproduct_code（10000XXX）で検索（フォールバック）
        product_code = order_item.get('product_code', '')
        if product_code:
            logger.debug(f"product_code {product_code} で検索（フォールバック）")
            
            result = self.supabase.table("product_master").select("*").eq("rakuten_sku", product_code).execute()
            
            if result.data:
                logger.info(f"✓ マッピング成功: product_code {product_code} → {result.data[0]['common_code']}")
                return result.data[0]
        
        logger.warning(f"✗ マッピング失敗: {product_code} (楽天SKU: {rakuten_item_number})")
        return None
    
    def test_improved_mapping(self):
        """改善されたマッピングのテスト"""
        logger.info("=== 改善されたマッピングテスト ===")
        
        # 最近の注文データを取得（テストデータを除外）
        orders = self.supabase.table("order_items").select("*").not_.like("product_code", "TEST%").limit(100).execute()
        
        if not orders.data:
            logger.error("注文データが見つかりません")
            return
        
        success_count = 0
        failed_count = 0
        failed_items = []
        
        for order in orders.data:
            mapping = self.find_product_mapping(order)
            
            if mapping:
                success_count += 1
            else:
                failed_count += 1
                failed_items.append({
                    'product_code': order.get('product_code'),
                    'rakuten_item_number': order.get('rakuten_item_number'),
                    'product_name': order.get('product_name', '')[:50]
                })
        
        total = success_count + failed_count
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        logger.info(f"\n=== テスト結果 ===")
        logger.info(f"総件数: {total}")
        logger.info(f"成功: {success_count} ({success_rate:.1f}%)")
        logger.info(f"失敗: {failed_count}")
        
        if failed_items:
            logger.info(f"\n失敗した商品の例:")
            for item in failed_items[:5]:
                logger.info(f"  - {item['product_code']} (楽天SKU: {item['rakuten_item_number']})")
                logger.info(f"    {item['product_name']}")
        
        return success_rate

def update_mapping_logic():
    """improved_mapping_system.pyのロジックを修正する案を生成"""
    logger.info("\n=== マッピングロジック修正案 ===")
    
    logger.info("""
現在の問題:
- _find_normal_product_mapping()がproduct_code（10000XXX）で検索している
- 実際の楽天SKUはrakuten_item_number（1XXX）に格納されている

修正案:
1. _find_normal_product_mapping()を以下のように修正:
   
   def _find_normal_product_mapping(self, product_code):
       # まず、注文データからrakuten_item_numberを取得
       order_item = self.supabase.table("order_items").select("rakuten_item_number").eq("product_code", product_code).limit(1).execute()
       
       if order_item.data and order_item.data[0].get('rakuten_item_number'):
           rakuten_sku = order_item.data[0]['rakuten_item_number']
           
           # rakuten_item_numberでマッピング検索
           result = self.supabase.table("product_master").select("*").eq("rakuten_sku", rakuten_sku).execute()
           
           if result.data:
               return result.data[0]
       
       # フォールバック: product_codeで検索
       result = self.supabase.table("product_master").select("*").eq("rakuten_sku", product_code).execute()
       return result.data[0] if result.data else None

2. より効率的な方法:
   - step1_extract_rakuten_sales()で、rakuten_item_numberも含めて返す
   - step2_map_to_common_codes()で直接rakuten_item_numberを使用
""")

if __name__ == "__main__":
    print("=== 楽天SKUマッピング修正テスト ===")
    
    system = FixedMappingSystem()
    
    # 改善されたマッピングをテスト
    success_rate = system.test_improved_mapping()
    
    if success_rate > 80:
        print(f"\n🎉 マッピング成功率が {success_rate:.1f}% に改善しました！")
    else:
        print(f"\n⚠️ マッピング成功率: {success_rate:.1f}%")
        print("追加の調整が必要です")
    
    # 修正案を表示
    update_mapping_logic()