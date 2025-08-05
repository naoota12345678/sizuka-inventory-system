#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
シンプルなマッピング失敗商品チェッカー
失敗リストの表示と再マッピング機能
"""

import os
import logging
from supabase import create_client

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

from fix_rakuten_sku_mapping import FixedMappingSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class SimpleMappingChecker:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.mapping_system = FixedMappingSystem()
    
    def get_failed_mappings(self, limit=100):
        """マッピング失敗商品のリストを取得"""
        print(f"マッピング失敗商品をチェック中... (最大{limit}件)")
        
        # order_itemsを取得（TESTデータ除外）
        result = self.supabase.table("order_items").select("*").not_.like("product_code", "TEST%").limit(limit).execute()
        
        failed_items = []
        success_count = 0
        
        for item in result.data:
            try:
                mapping = self.mapping_system.find_product_mapping(item)
                if mapping:
                    success_count += 1
                else:
                    failed_items.append({
                        "id": item["id"],
                        "product_code": item.get("product_code"),
                        "rakuten_item_number": item.get("rakuten_item_number"),
                        "choice_code": item.get("choice_code"),
                        "order_number": item.get("order_number"),
                        "created_at": item.get("created_at")
                    })
            except Exception as e:
                logger.error(f"エラー ID {item.get('id')}: {str(e)}")
        
        total = len(result.data)
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        print(f"\\n=== 結果 ===")
        print(f"総件数: {total}")
        print(f"成功: {success_count}")
        print(f"失敗: {len(failed_items)}")
        print(f"成功率: {success_rate:.1f}%")
        
        return failed_items, success_rate
    
    def show_failed_list(self, failed_items):
        """失敗リストを表示"""
        if not failed_items:
            print("\\nマッピング失敗商品はありません！")
            return
        
        print(f"\\n=== マッピング失敗商品リスト ({len(failed_items)}件) ===")
        print("-" * 80)
        
        for i, item in enumerate(failed_items[:20], 1):  # 最初の20件のみ表示
            print(f"{i:2d}. ID:{item['id']} | Order:{item['order_number']}")
            print(f"    Product Code: {item['product_code']}")
            print(f"    Rakuten SKU: {item['rakuten_item_number']}")
            print(f"    Choice Code: {item['choice_code']}")
            print(f"    作成日: {item['created_at']}")
            print()
        
        if len(failed_items) > 20:
            print(f"... 他 {len(failed_items) - 20}件")
    
    def retry_mapping_for_failed_items(self, failed_items):
        """失敗した商品の再マッピングを実行"""
        if not failed_items:
            print("再マッピング対象がありません")
            return
        
        print(f"\\n=== 再マッピング実行 ===")
        print(f"対象: {len(failed_items)}件")
        
        success_count = 0
        still_failed = []
        
        for item in failed_items:
            try:
                # 再度マッピングを試行
                order_item = self.supabase.table("order_items").select("*").eq("id", item["id"]).execute().data[0]
                mapping = self.mapping_system.find_product_mapping(order_item)
                
                if mapping:
                    print(f"成功: ID {item['id']} → {mapping['common_code']}")
                    success_count += 1
                else:
                    still_failed.append(item)
                    print(f"失敗: ID {item['id']} - まだマッピングできません")
                    
            except Exception as e:
                print(f"エラー: ID {item['id']} - {str(e)}")
                still_failed.append(item)
        
        print(f"\\n=== 再マッピング結果 ===")
        print(f"再試行した: {len(failed_items)}件")
        print(f"成功: {success_count}件") 
        print(f"まだ失敗: {len(still_failed)}件")
        
        if success_count > 0:
            print(f"\\n改善率: {success_count/len(failed_items)*100:.1f}%")
        
        return still_failed

def main():
    checker = SimpleMappingChecker()
    
    print("シンプルマッピングチェッカー")
    print("=" * 40)
    
    while True:
        print("\\n選択してください:")
        print("1. マッピング失敗リストを表示")
        print("2. 再マッピングを実行")
        print("3. 終了")
        
        choice = input("\\n選択 (1-3): ").strip()
        
        if choice == "1":
            print("\\nチェック件数を選択:")
            print("1. 50件（テスト）")
            print("2. 200件（標準）")
            print("3. 500件（詳細）")
            
            limit_choice = input("選択 (1-3): ").strip()
            limit_map = {"1": 50, "2": 200, "3": 500}
            limit = limit_map.get(limit_choice, 200)
            
            failed_items, success_rate = checker.get_failed_mappings(limit)
            checker.show_failed_list(failed_items)
            
            # グローバル変数として失敗リストを保存
            globals()['last_failed_items'] = failed_items
            
        elif choice == "2":
            # 前回の失敗リストがあるかチェック
            if 'last_failed_items' in globals():
                failed_items = globals()['last_failed_items']
                print(f"\\n前回の失敗リスト({len(failed_items)}件)で再マッピングを実行しますか？")
                confirm = input("実行する場合は 'y' を入力: ")
                
                if confirm.lower() == 'y':
                    still_failed = checker.retry_mapping_for_failed_items(failed_items)
                    # 結果を更新
                    globals()['last_failed_items'] = still_failed
                else:
                    print("キャンセルしました")
            else:
                print("\\n先にマッピング失敗リストを表示してください（選択肢1）")
                
        elif choice == "3":
            print("終了します")
            break
        else:
            print("無効な選択です")

if __name__ == "__main__":
    main()