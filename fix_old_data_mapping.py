#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
既存の古いorder_itemsデータの楽天SKUを修正してマッピングを復旧
"""

import logging
from supabase import create_client
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class OldDataFixer:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
    def extract_sku_from_extended_data(self, order_item):
        """extended_rakuten_dataから楽天SKUを抽出"""
        extended_data = order_item.get('extended_rakuten_data', {})
        if not extended_data or not isinstance(extended_data, dict):
            return None
            
        # raw_sku_dataから抽出
        raw_sku_data = extended_data.get('raw_sku_data', {})
        if raw_sku_data:
            # extracted_skuがある場合
            extracted_sku = raw_sku_data.get('extracted_sku')
            if extracted_sku:
                return str(extracted_sku)
                
            # original_sku_infoから抽出
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
    
    def convert_product_code_to_sku(self, product_code):
        """product_code (10000XXX) から楽天SKU (1XXX) への変換を試行"""
        if not product_code or not isinstance(product_code, str):
            return None
            
        # 10000XXXパターンの場合、末尾3-4桁を抽出
        if product_code.startswith('10000') and len(product_code) >= 8:
            # 10000059 -> 1059 -> 1759? いろいろな変換パターンを試す
            possible_skus = []
            
            # パターン1: 末尾3桁 (10000059 -> 059 -> 1059)
            last_3 = product_code[-3:]
            possible_skus.append(f"1{last_3}")
            
            # パターン2: 末尾2桁 (10000059 -> 59 -> 1759)  
            last_2 = product_code[-2:]
            possible_skus.append(f"17{last_2}")
            
            # パターン3: 末尾4桁そのまま (10000059 -> 0059)
            last_4 = product_code[-4:]
            possible_skus.append(last_4)
            
            # パターン4: より複雑な変換パターン
            # 10000059 -> 1765のような変換があるかも
            # これは実際のマッピングテーブルを参照する必要がある
            
            return possible_skus
        
        return None
    
    def find_sku_by_conversion_patterns(self, product_code):
        """変換パターンを使って正しい楽天SKUを見つける"""
        possible_skus = self.convert_product_code_to_sku(product_code)
        if not possible_skus:
            return None
            
        # 各変換パターンでproduct_masterを検索
        for sku in possible_skus:
            try:
                result = self.supabase.table("product_master").select("*").eq("rakuten_sku", sku).execute()
                if result.data:
                    logger.debug(f"Found mapping: {product_code} -> {sku} -> {result.data[0]['common_code']}")
                    return sku
            except Exception as e:
                logger.debug(f"Error checking SKU {sku}: {e}")
                continue
                
        return None
    
    def analyze_existing_mapping_patterns(self):
        """既存の正しいマッピングパターンを分析"""
        logger.info("=== 既存マッピングパターン分析 ===")
        
        # rakuten_item_numberが設定済みのデータを取得
        result = self.supabase.table("order_items").select("product_code, rakuten_item_number").not_.is_("rakuten_item_number", "null").not_.like("product_code", "TEST%").limit(50).execute()
        
        patterns = {}
        for item in result.data:
            product_code = item.get('product_code')
            sku = item.get('rakuten_item_number')
            if product_code and sku:
                patterns[product_code] = sku
                
        logger.info(f"発見されたパターン: {len(patterns)}件")
        for product_code, sku in list(patterns.items())[:10]:
            logger.info(f"  {product_code} -> {sku}")
            
        return patterns
    
    def fix_old_order_items(self, batch_size=100):
        """古いorder_itemsのrakuten_item_numberを修正"""
        logger.info("=== 古いorder_itemsデータ修正 ===")
        
        # 既存パターンを分析
        known_patterns = self.analyze_existing_mapping_patterns()
        
        # rakuten_item_numberがNullの古いデータを取得
        result = self.supabase.table("order_items").select("*").is_("rakuten_item_number", "null").not_.like("product_code", "TEST%").limit(batch_size).execute()
        
        logger.info(f"修正対象: {len(result.data)}件")
        
        updated_count = 0
        failed_count = 0
        
        for order in result.data:
            try:
                product_code = order.get('product_code')
                order_id = order.get('id')
                
                # 方法1: 既知のパターンから検索
                if product_code in known_patterns:
                    correct_sku = known_patterns[product_code]
                    logger.info(f"既知パターン使用: {product_code} -> {correct_sku}")
                else:
                    # 方法2: extended_rakuten_dataから抽出
                    correct_sku = self.extract_sku_from_extended_data(order)
                    
                    if not correct_sku:
                        # 方法3: 変換パターンで検索
                        correct_sku = self.find_sku_by_conversion_patterns(product_code)
                
                if correct_sku:
                    # rakuten_item_numberを更新
                    update_result = self.supabase.table("order_items").update({
                        "rakuten_item_number": correct_sku
                    }).eq("id", order_id).execute()
                    
                    if update_result.data:
                        logger.info(f"✓ 更新: ID {order_id} {product_code} -> {correct_sku}")
                        updated_count += 1
                        
                        # 新しく発見したパターンを記録
                        if product_code not in known_patterns:
                            known_patterns[product_code] = correct_sku
                    else:
                        logger.error(f"✗ 更新失敗: ID {order_id}")
                        failed_count += 1
                else:
                    logger.warning(f"SKU特定失敗: ID {order_id} {product_code}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"エラー: ID {order.get('id')} - {str(e)}")
                failed_count += 1
        
        logger.info(f"\n=== 修正結果 ===")
        logger.info(f"更新成功: {updated_count}件")
        logger.info(f"失敗: {failed_count}件")
        
        return updated_count, failed_count
    
    def verify_mapping_improvement(self):
        """マッピング改善効果を確認"""
        logger.info("=== マッピング改善効果確認 ===")
        
        # 全体の統計
        total_result = self.supabase.table("order_items").select("id").not_.like("product_code", "TEST%").execute()
        total_count = len(total_result.data)
        
        # rakuten_item_numberがあるもの
        with_sku_result = self.supabase.table("order_items").select("id").not_.is_("rakuten_item_number", "null").not_.like("product_code", "TEST%").execute()
        with_sku_count = len(with_sku_result.data)
        
        # 実際にマッピングできるもの（サンプル50件でテスト）
        from fix_rakuten_sku_mapping import FixedMappingSystem
        mapping_system = FixedMappingSystem()
        
        sample_result = self.supabase.table("order_items").select("*").not_.like("product_code", "TEST%").limit(50).execute()
        
        mappable_count = 0
        for order in sample_result.data:
            mapping = mapping_system.find_product_mapping(order)
            if mapping:
                mappable_count += 1
        
        sample_total = len(sample_result.data)
        estimated_mappable = int((mappable_count / sample_total) * total_count) if sample_total > 0 else 0
        
        logger.info(f"総件数: {total_count}")
        logger.info(f"rakuten_item_number設定済み: {with_sku_count} ({with_sku_count/total_count*100:.1f}%)")
        logger.info(f"実際マッピング可能(推定): {estimated_mappable} ({mappable_count/sample_total*100:.1f}%)")
        
        return {
            'total_count': total_count,
            'with_sku_count': with_sku_count,
            'estimated_mappable': estimated_mappable,
            'mapping_rate': mappable_count/sample_total*100 if sample_total > 0 else 0
        }

def main():
    fixer = OldDataFixer()
    
    # 現在の状況確認
    print("=== 修正前の状況確認 ===")
    stats_before = fixer.verify_mapping_improvement()
    
    # 古いデータの修正実行
    print(f"\n古いデータの修正を実行しますか？")
    print(f"対象: rakuten_item_numberがNullの古いorder_items")
    
    response = input("実行する場合は 'y' を入力: ")
    if response.lower() == 'y':
        print("\n=== 古いデータ修正実行 ===")
        
        # バッチ処理で修正
        total_updated = 0
        total_failed = 0
        batch_count = 0
        
        while True:
            batch_count += 1
            print(f"\nバッチ {batch_count} 実行中...")
            
            updated, failed = fixer.fix_old_order_items(batch_size=100)
            total_updated += updated
            total_failed += failed
            
            if updated == 0:  # もう更新するデータがない
                break
                
            if batch_count >= 10:  # 安全のため10バッチまで
                print("10バッチ完了。続行する場合は再実行してください。")
                break
        
        print(f"\n=== 全体修正結果 ===")
        print(f"総更新件数: {total_updated}")
        print(f"総失敗件数: {total_failed}")
        
        # 修正後の状況確認
        print("\n=== 修正後の状況確認 ===")
        stats_after = fixer.verify_mapping_improvement()
        
        print(f"\n=== 改善効果 ===")
        print(f"マッピング率: {stats_before['mapping_rate']:.1f}% → {stats_after['mapping_rate']:.1f}%")
        print(f"SKU設定済み: {stats_before['with_sku_count']} → {stats_after['with_sku_count']} (+{stats_after['with_sku_count'] - stats_before['with_sku_count']})")
    else:
        print("修正をキャンセルしました")

if __name__ == "__main__":
    main()