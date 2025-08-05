#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
マッピング失敗項目を分析・一覧出力するツール
3種類のマッピング基本表との連携確認も含む
"""

import os
import logging
import json
from datetime import datetime
from supabase import create_client

# 環境変数を設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

from fix_rakuten_sku_mapping import FixedMappingSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

class MappingFailureAnalyzer:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.mapping_system = FixedMappingSystem()
        
        # 3種類のGoogle Sheetsマッピング表定義
        self.google_sheets_info = {
            "product_mapping": {
                "name": "商品番号マッピング基本表",
                "gid": "1290908701",
                "description": "楽天SKU → 共通コードマッピング"
            },
            "choice_mapping": {
                "name": "選択肢コード対応表", 
                "gid": "1695475455",
                "description": "選択肢コード（R05等） → 共通コードマッピング"
            },
            "bundle_components": {
                "name": "まとめ商品内訳テーブル",
                "gid": "1670260677", 
                "description": "まとめ商品の構成要素マッピング"
            }
        }
        
    def analyze_mapping_failures(self, limit=100):
        """マッピング失敗の詳細分析"""
        logger.info("=== マッピング失敗分析開始 ===")
        
        # 全order_itemsを取得（TESTデータ除外）
        result = self.supabase.table("order_items").select("*").not_.like("product_code", "TEST%").limit(limit).execute()
        
        total_items = len(result.data)
        logger.info(f"分析対象: {total_items}件")
        
        failures = []
        successes = []
        
        for order in result.data:
            try:
                mapping = self.mapping_system.find_product_mapping(order)
                
                analysis_result = {
                    "id": order.get("id"),
                    "product_code": order.get("product_code"),
                    "rakuten_item_number": order.get("rakuten_item_number"),
                    "choice_code": order.get("choice_code"),
                    "order_number": order.get("order_number"),
                    "created_at": order.get("created_at"),
                    "mapping_result": mapping,
                    "failure_reasons": []
                }
                
                if mapping:
                    analysis_result["status"] = "success"
                    analysis_result["mapped_to"] = mapping.get("common_code")
                    successes.append(analysis_result)
                else:
                    analysis_result["status"] = "failure"
                    # 失敗理由を詳細分析
                    analysis_result["failure_reasons"] = self._analyze_failure_reasons(order)
                    failures.append(analysis_result)
                    
            except Exception as e:
                logger.error(f"分析エラー ID {order.get('id')}: {str(e)}")
                
        logger.info(f"\\n=== 分析結果 ===")
        logger.info(f"成功: {len(successes)}件")
        logger.info(f"失敗: {len(failures)}件")
        logger.info(f"成功率: {len(successes)/total_items*100:.1f}%")
        
        return {
            "total": total_items,
            "successes": successes,
            "failures": failures,
            "success_rate": len(successes)/total_items*100 if total_items > 0 else 0
        }
    
    def _analyze_failure_reasons(self, order):
        """失敗理由の詳細分析"""
        reasons = []
        
        product_code = order.get("product_code")
        rakuten_sku = order.get("rakuten_item_number")
        choice_code = order.get("choice_code")
        
        # 1. 楽天SKUが存在するか確認
        if rakuten_sku:
            try:
                sku_result = self.supabase.table("product_master").select("*").eq("rakuten_sku", rakuten_sku).execute()
                if not sku_result.data:
                    reasons.append(f"楽天SKU '{rakuten_sku}' がproduct_masterに存在しない")
            except Exception as e:
                reasons.append(f"楽天SKU検索エラー: {str(e)}")
        else:
            reasons.append("rakuten_item_numberが未設定")
        
        # 2. 選択肢コードの確認
        if choice_code:
            # 選択肢コードを抽出
            import re
            pattern = r'[A-Z]\d{2}'
            extracted_codes = re.findall(pattern, choice_code)
            
            if extracted_codes:
                for code in extracted_codes:
                    try:
                        choice_result = self.supabase.table("choice_code_mapping").select("*").filter("choice_info->>choice_code", "eq", code).execute()
                        if not choice_result.data:
                            reasons.append(f"選択肢コード '{code}' がchoice_code_mappingに存在しない")
                    except Exception as e:
                        reasons.append(f"選択肢コード '{code}' 検索エラー: {str(e)}")
            else:
                reasons.append(f"選択肢コード '{choice_code}' から有効なコードが抽出できない")
        
        # 3. product_codeの問題
        if product_code and product_code.startswith("10000"):
            reasons.append(f"古いproduct_code形式 '{product_code}' - rakuten_item_numberへの変換が必要")
        
        return reasons
    
    def output_failure_report(self, analysis_result, output_file=None):
        """失敗レポートを出力"""
        logger.info("=== マッピング失敗レポート出力 ===")
        
        failures = analysis_result["failures"]
        
        if not failures:
            logger.info("マッピング失敗がありません！")
            return
        
        # ファイル出力先を決定
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"mapping_failures_{timestamp}.txt"
        
        # 失敗理由別の集計
        reason_counts = {}
        for failure in failures:
            for reason in failure["failure_reasons"]:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        # レポート内容を作成
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("マッピング失敗詳細レポート")
        report_lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)
        
        report_lines.append(f"\\n📊 概要:")
        report_lines.append(f"  総件数: {analysis_result['total']}件")
        report_lines.append(f"  成功: {len(analysis_result['successes'])}件")
        report_lines.append(f"  失敗: {len(failures)}件")
        report_lines.append(f"  成功率: {analysis_result['success_rate']:.1f}%")
        
        report_lines.append(f"\\n🔍 失敗理由別統計:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
            report_lines.append(f"  {count:3d}件: {reason}")
        
        report_lines.append(f"\\n📋 失敗項目詳細:")
        report_lines.append("-" * 80)
        
        for i, failure in enumerate(failures[:50], 1):  # 最初の50件のみ詳細出力
            report_lines.append(f"\\n{i:2d}. ID: {failure['id']} | Order: {failure['order_number']}")
            report_lines.append(f"    Product Code: {failure['product_code']}")
            report_lines.append(f"    Rakuten SKU: {failure['rakuten_item_number']}")
            report_lines.append(f"    Choice Code: {failure['choice_code']}")
            report_lines.append(f"    作成日: {failure['created_at']}")
            report_lines.append(f"    失敗理由:")
            for reason in failure['failure_reasons']:
                report_lines.append(f"      - {reason}")
        
        if len(failures) > 50:
            report_lines.append(f"\\n（他 {len(failures) - 50}件の失敗項目は省略）")
        
        # Google Sheets同期状況
        report_lines.append(f"\\n🔗 Google Sheets マッピング表情報:")
        report_lines.append("-" * 50)
        for key, info in self.google_sheets_info.items():
            report_lines.append(f"  {info['name']} (gid={info['gid']})")
            report_lines.append(f"    用途: {info['description']}")
            report_lines.append(f"    URL: https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/edit#gid={info['gid']}")
        
        report_lines.append(f"\\n💡 推奨対応:")
        report_lines.append("  1. Google Sheetsのマッピング表を更新")
        report_lines.append("  2. 定期同期スクリプトを実行")
        report_lines.append("  3. 新しい楽天SKUや選択肢コードを追加")
        report_lines.append("  4. 再度マッピングテストを実行")
        
        # ファイルに出力
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\\n'.join(report_lines))
            logger.info(f"レポートを出力しました: {output_file}")
        except Exception as e:
            logger.error(f"ファイル出力エラー: {e}")
        
        # コンソールにも要約を出力
        print("\\n" + "=" * 60)
        print("マッピング失敗項目要約")
        print("=" * 60)
        print(f"失敗件数: {len(failures)}件 / 全{analysis_result['total']}件")
        print(f"成功率: {analysis_result['success_rate']:.1f}%")
        print("\\n主な失敗理由:")
        for reason, count in list(sorted(reason_counts.items(), key=lambda x: x[1], reverse=True))[:5]:
            print(f"  {count}件: {reason}")
        print(f"\\n詳細レポート: {output_file}")
        
        return output_file
    
    def check_google_sheets_sync_status(self):
        """Google Sheetsとの同期状況を確認"""
        logger.info("=== Google Sheets同期状況確認 ===")
        
        sync_status = {}
        
        # 1. product_master (商品番号マッピング基本表)
        product_count = len(self.supabase.table("product_master").select("id").not_.is_("rakuten_sku", "null").execute().data)
        sync_status["product_mapping"] = {
            "table": "product_master",
            "count": product_count,
            "description": "楽天SKU → 共通コード"
        }
        
        # 2. choice_code_mapping (選択肢コード対応表)
        choice_count = len(self.supabase.table("choice_code_mapping").select("id").execute().data)
        sync_status["choice_mapping"] = {
            "table": "choice_code_mapping", 
            "count": choice_count,
            "description": "選択肢コード → 共通コード"
        }
        
        # 3. package_components (まとめ商品内訳テーブル) - テーブルが存在しない場合は0
        try:
            package_count = len(self.supabase.table("package_components").select("id").execute().data)
        except:
            package_count = 0
        sync_status["bundle_components"] = {
            "table": "package_components",
            "count": package_count,
            "description": "まとめ商品構成要素"
        }
        
        # 結果出力
        print("\\nマッピングテーブル同期状況:")
        print("-" * 60)
        for key, status in sync_status.items():
            sheet_info = self.google_sheets_info[key]
            print(f"{sheet_info['name']}: {status['count']}件")
            print(f"  → {status['description']}")
            print(f"  → Google Sheets (gid={sheet_info['gid']})")
            
            # 推奨同期頻度
            if status['count'] < 100:
                print(f"  注意: データが少ない - 初回同期が必要")
            else:
                print(f"  OK: データ存在 - 定期同期推奨")
            print()
        
        return sync_status

def main():
    analyzer = MappingFailureAnalyzer()
    
    print("マッピング失敗項目分析ツール")
    print("=" * 50)
    
    # Google Sheets同期状況確認
    analyzer.check_google_sheets_sync_status()
    
    # マッピング失敗分析実行
    print("\\nマッピング失敗分析を実行しますか？")
    print("分析件数を選択してください:")
    print("  1. 50件（テスト）")
    print("  2. 200件（標準）") 
    print("  3. 全件（時間がかかります）")
    
    choice = input("選択 (1-3): ").strip()
    
    limit_map = {"1": 50, "2": 200, "3": 10000}
    limit = limit_map.get(choice, 200)
    
    print(f"\\n{limit}件の分析を開始...")
    analysis_result = analyzer.analyze_mapping_failures(limit)
    
    # レポート出力
    if analysis_result["failures"]:
        print("\\n失敗レポートを出力しますか？ (y/n): ", end="")
        if input().lower() == 'y':
            output_file = analyzer.output_failure_report(analysis_result)
            print(f"\\n完了: {output_file}")
    else:
        print("\\nマッピング失敗はありませんでした！")

if __name__ == "__main__":
    main()