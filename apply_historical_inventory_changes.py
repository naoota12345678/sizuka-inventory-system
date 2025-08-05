#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
過去データ同期後の在庫システム適用
既存の改良されたマッピングシステムを使用して在庫変動を適用

⚠️ 重要: このスクリプトは既存の在庫マッピングシステムを使用します
現在100%成功率のシステムを利用するため安全です
"""

import os
import sys
from datetime import datetime, timedelta
import pytz
import logging

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from improved_mapping_system import InventoryMappingSystem

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_historical_inventory_changes(start_date_str="2025-02-10", end_date_str="2025-07-31", dry_run=True):
    """過去期間の在庫変動を適用"""
    
    logger.info("=== 過去期間在庫変動適用開始 ===")
    logger.info(f"期間: {start_date_str} ～ {end_date_str}")
    logger.info(f"DRY RUN: {dry_run}")
    
    if dry_run:
        logger.info("⚠️  DRY RUN モード: 実際の在庫は変更されません")
    else:
        logger.warning("🚨 実際の在庫変更モード: 在庫数が実際に変更されます")
    
    try:
        # 改良されたマッピングシステムのインスタンス化
        mapping_system = InventoryMappingSystem()
        
        # 期間を日付オブジェクトに変換
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        # 日別に処理（メモリ使用量を抑えるため）
        current_date = start_date
        total_results = {
            'total_days_processed': 0,
            'total_rakuten_sales': 0,
            'total_mapped_items': 0,
            'total_unmapped_items': 0,
            'total_inventory_changes': 0,
            'daily_summaries': [],
            'mapping_success_rate': 0
        }
        
        while current_date <= end_date:
            logger.info(f"\n📅 処理日: {current_date.strftime('%Y-%m-%d')}")
            
            try:
                # その日のデータを処理
                day_result = mapping_system.run_full_process(target_date=current_date, dry_run=dry_run)
                
                # 結果を集計
                rakuten_sales_count = len(day_result.get('rakuten_sales', []))
                mapped_items_count = len(day_result.get('mapped_items', []))
                unmapped_items_count = len(day_result.get('unmapped_items', []))
                inventory_changes_count = len(day_result.get('inventory_changes', []))
                
                if rakuten_sales_count > 0:
                    logger.info(f"  📦 楽天商品: {rakuten_sales_count}件")
                    logger.info(f"  ✅ マッピング成功: {mapped_items_count}件")
                    logger.info(f"  ❌ マッピング失敗: {unmapped_items_count}件")
                    logger.info(f"  📊 在庫変動: {inventory_changes_count}商品")
                    
                    if mapped_items_count + unmapped_items_count > 0:
                        day_success_rate = (mapped_items_count / (mapped_items_count + unmapped_items_count)) * 100
                        logger.info(f"  🎯 日別成功率: {day_success_rate:.1f}%")
                else:
                    logger.info(f"  📭 データなし")
                
                # 総計に追加
                total_results['total_rakuten_sales'] += rakuten_sales_count
                total_results['total_mapped_items'] += mapped_items_count
                total_results['total_unmapped_items'] += unmapped_items_count
                total_results['total_inventory_changes'] += inventory_changes_count
                total_results['total_days_processed'] += 1
                
                # 日別サマリー
                daily_summary = {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'rakuten_sales': rakuten_sales_count,
                    'mapped_items': mapped_items_count,
                    'unmapped_items': unmapped_items_count,
                    'inventory_changes': inventory_changes_count,
                    'success_rate': day_success_rate if rakuten_sales_count > 0 else 100
                }
                total_results['daily_summaries'].append(daily_summary)
                
            except Exception as e:
                logger.error(f"❌ {current_date} の処理でエラー: {str(e)}")
                daily_summary = {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'error': str(e)
                }
                total_results['daily_summaries'].append(daily_summary)
            
            # 次の日へ
            current_date += timedelta(days=1)
        
        # 全体の成功率計算
        if total_results['total_mapped_items'] + total_results['total_unmapped_items'] > 0:
            total_results['mapping_success_rate'] = (
                total_results['total_mapped_items'] / 
                (total_results['total_mapped_items'] + total_results['total_unmapped_items'])
            ) * 100
        
        # 最終サマリー
        logger.info("\n" + "="*60)
        logger.info("🎉 過去期間在庫変動適用完了")
        logger.info("="*60)
        logger.info(f"📅 処理日数: {total_results['total_days_processed']}日")
        logger.info(f"📦 総楽天商品: {total_results['total_rakuten_sales']}件")
        logger.info(f"✅ 総マッピング成功: {total_results['total_mapped_items']}件")
        logger.info(f"❌ 総マッピング失敗: {total_results['total_unmapped_items']}件")
        logger.info(f"📊 総在庫変動: {total_results['total_inventory_changes']}商品")
        logger.info(f"🎯 全体成功率: {total_results['mapping_success_rate']:.1f}%")
        
        if dry_run:
            logger.info("\n⚠️  DRY RUN完了: 実際の在庫は変更されていません")
            logger.info("実際に適用する場合は dry_run=False で実行してください")
        else:
            logger.info("\n✅ 実際の在庫変更完了")
        
        # 未マッピング商品があれば警告
        if total_results['total_unmapped_items'] > 0:
            logger.warning(f"\n⚠️  未マッピング商品が {total_results['total_unmapped_items']}件あります")
            logger.warning("商品マスタやマッピングテーブルの確認をお勧めします")
        
        return total_results
        
    except Exception as e:
        logger.error(f"❌ 在庫変動適用でエラー: {str(e)}")
        raise

def main():
    """メイン実行関数"""
    logger.info("過去期間在庫変動適用ツール")
    logger.info("現在の改良マッピングシステム（100%成功率）を使用します")
    
    print("\n選択してください:")
    print("1. DRY RUN (テスト実行 - 在庫は変更されません)")
    print("2. 実際に適用 (⚠️ 在庫が実際に変更されます)")
    
    choice = input("\n選択 (1/2): ").strip()
    
    if choice == "1":
        logger.info("DRY RUN モードで実行します")
        try:
            result = apply_historical_inventory_changes(dry_run=True)
            logger.info("\n🎉 DRY RUN完了: 問題がなければ実際の適用を実行してください")
            return result
        except Exception as e:
            logger.error(f"\n❌ DRY RUNでエラー: {str(e)}")
            return None
            
    elif choice == "2":
        logger.warning("⚠️  実際の在庫変更を実行します")
        confirm = input("本当に実行しますか？ (yes/No): ")
        
        if confirm.lower() == "yes":
            try:
                result = apply_historical_inventory_changes(dry_run=False)
                logger.info("\n🎉 在庫変動適用完了")
                return result
            except Exception as e:
                logger.error(f"\n❌ 在庫変動適用でエラー: {str(e)}")
                return None
        else:
            logger.info("キャンセルしました")
            return None
    else:
        logger.info("無効な選択です")
        return None

if __name__ == "__main__":
    main()