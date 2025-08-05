#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在庫テーブルのcommon_codeを正しい値に修正
スマレジID（10003等）→正しい共通コード（CM001等）
"""

import os
import logging
import requests
import csv
from io import StringIO
from supabase import create_client

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class InventoryCommonCodeFixer:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
    def get_google_sheets_mapping(self):
        """Google Sheetsからマッピング基本表を取得"""
        csv_url = 'https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/export?format=csv&gid=1290908701'
        
        try:
            response = requests.get(csv_url, timeout=30)
            if response.status_code != 200:
                raise Exception(f"Google Sheets取得エラー: {response.status_code}")
            
            csv_data = StringIO(response.text)
            reader = csv.reader(csv_data)
            
            mapping = {}  # スマレジID → 共通コード
            
            for i, row in enumerate(reader):
                if i == 0:  # ヘッダー行スキップ
                    continue
                    
                if len(row) >= 2:
                    smaregi_id = row[0].strip() if row[0] else None  # A列: スマレジID
                    common_code = row[1].strip() if row[1] else None  # B列: 共通コード
                    
                    # スマレジID（10XXX形式）→共通コード（CMXXX形式）のマッピング
                    if smaregi_id and common_code and smaregi_id.startswith('10'):
                        mapping[smaregi_id] = common_code
            
            logger.info(f"Google Sheetsから{len(mapping)}件のマッピングを取得")
            return mapping
            
        except Exception as e:
            logger.error(f"Google Sheetsマッピング取得エラー: {str(e)}")
            return {}
    
    def get_product_master_mapping(self):
        """product_masterテーブルからマッピングを取得"""
        try:
            result = self.supabase.table("product_master").select("rakuten_sku, common_code").not_.is_("common_code", "null").execute()
            
            mapping = {}  # 楽天SKU → 共通コード
            for item in result.data:
                rakuten_sku = item.get('rakuten_sku')
                common_code = item.get('common_code')
                if rakuten_sku and common_code:
                    mapping[str(rakuten_sku)] = common_code
            
            logger.info(f"product_masterから{len(mapping)}件のマッピングを取得")
            return mapping
            
        except Exception as e:
            logger.error(f"product_masterマッピング取得エラー: {str(e)}")
            return {}
    
    def analyze_inventory_common_codes(self):
        """現在のinventoryテーブルのcommon_code状況を分析"""
        try:
            result = self.supabase.table("inventory").select("id, common_code, product_name").execute()
            
            analysis = {
                "total": len(result.data),
                "smaregi_format": 0,  # 10XXX形式
                "cm_format": 0,       # CMXXX形式
                "other_format": 0,    # その他
                "examples": {
                    "smaregi": [],
                    "cm": [],
                    "other": []
                }
            }
            
            for item in result.data:
                common_code = item.get('common_code', '')
                
                if common_code.startswith('10') and len(common_code) >= 5:
                    analysis["smaregi_format"] += 1
                    if len(analysis["examples"]["smaregi"]) < 5:
                        analysis["examples"]["smaregi"].append(common_code)
                elif common_code.startswith('CM'):
                    analysis["cm_format"] += 1
                    if len(analysis["examples"]["cm"]) < 5:
                        analysis["examples"]["cm"].append(common_code)
                else:
                    analysis["other_format"] += 1
                    if len(analysis["examples"]["other"]) < 5:
                        analysis["examples"]["other"].append(common_code)
            
            return analysis
            
        except Exception as e:
            logger.error(f"inventory分析エラー: {str(e)}")
            return {}
    
    def fix_inventory_common_codes(self):
        """inventoryテーブルのcommon_codeを修正"""
        print("=== inventoryテーブルのcommon_code修正 ===")
        
        # 現状分析
        analysis = self.analyze_inventory_common_codes()
        if analysis:
            print(f"\n現状分析:")
            print(f"  総件数: {analysis['total']}")
            print(f"  スマレジ形式 (10XXX): {analysis['smaregi_format']}件")
            print(f"  CM形式 (CMXXX): {analysis['cm_format']}件")
            print(f"  その他: {analysis['other_format']}件")
            
            if analysis['smaregi_format'] > 0:
                print(f"\nスマレジ形式の例: {analysis['examples']['smaregi']}")
            if analysis['cm_format'] > 0:
                print(f"CM形式の例: {analysis['examples']['cm']}")
            if analysis['other_format'] > 0:
                print(f"その他の例: {analysis['examples']['other']}")
        
        # Google Sheetsからマッピング取得
        google_mapping = self.get_google_sheets_mapping()
        product_mapping = self.get_product_master_mapping()
        
        if not google_mapping and not product_mapping:
            print("\\nエラー: マッピングデータを取得できませんでした")
            return False
        
        print(f"\nマッピングデータ:")
        print(f"  Google Sheets: {len(google_mapping)}件")
        print(f"  product_master: {len(product_mapping)}件")
        
        # 修正確認
        if analysis.get('smaregi_format', 0) > 0:
            response = input(f"\n{analysis['smaregi_format']}件のスマレジ形式を正しい共通コードに変換しますか？ (y/n): ")
            if response.lower() != 'y':
                print("キャンセルしました")
                return False
        else:
            print("\n修正が必要なデータはありません")
            return True
        
        # 修正実行
        updated_count = 0
        failed_count = 0
        
        try:
            # スマレジ形式のcommon_codeを持つ在庫を取得
            result = self.supabase.table("inventory").select("id, common_code").execute()
            
            for item in result.data:
                common_code = item.get('common_code', '')
                item_id = item.get('id')
                
                if common_code.startswith('10') and len(common_code) >= 5:
                    # Google Sheetsマッピングで変換を試行
                    correct_code = google_mapping.get(common_code)
                    
                    if not correct_code:
                        # product_masterマッピングでも試行
                        correct_code = product_mapping.get(common_code)
                    
                    if correct_code:
                        # 更新実行
                        update_result = self.supabase.table("inventory").update({
                            "common_code": correct_code
                        }).eq("id", item_id).execute()
                        
                        if update_result.data:
                            print(f"OK ID {item_id}: {common_code} → {correct_code}")
                            updated_count += 1
                        else:
                            print(f"NG ID {item_id}: 更新失敗")
                            failed_count += 1
                    else:
                        print(f"警告 ID {item_id}: {common_code} のマッピングが見つかりません")
                        failed_count += 1
            
            print(f"\n=== 修正完了 ===")
            print(f"更新成功: {updated_count}件")
            print(f"失敗: {failed_count}件")
            
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"修正実行エラー: {str(e)}")
            return False

def main():
    fixer = InventoryCommonCodeFixer()
    
    print("在庫テーブル共通コード修正ツール")
    print("=" * 50)
    
    success = fixer.fix_inventory_common_codes()
    
    if success:
        print("\n修正が完了しました！")
        print("在庫ダッシュボードで正しい共通コードが表示されるはずです。")
    else:
        print("\n修正に問題がありました。")

if __name__ == "__main__":
    main()