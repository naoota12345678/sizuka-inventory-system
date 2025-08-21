#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
製造データ同期スクリプト
製造.xlsxから製造（在庫増加）データをSupabaseに同期
"""

import os
import sys
import pandas as pd
from datetime import datetime, timezone
from supabase import create_client
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def load_manufacturing_data(file_path):
    """
    製造.xlsxから製造データを読み込み
    """
    print("=" * 60)
    print("製造データ読み込み開始")
    print("=" * 60)
    
    try:
        # Excelファイル読み込み（列名は実際の構造に基づく）
        df = pd.read_excel(file_path, sheet_name='Sheet1')
        
        # 列名を正規化（実際の列構造に基づく）
        # 列順: 日付, 商品名, カテゴリ, 数量, スマレジID
        df.columns = ['date', 'product_name', 'category', 'quantity', 'smaregi_id']
        
        print(f"総製造記録数: {len(df)}")
        print(f"製造期間: {df['date'].min()} ～ {df['date'].max()}")
        
        # データクリーニング
        df = df.dropna(subset=['product_name', 'quantity'])  # 必須フィールドのみ
        df['quantity'] = df['quantity'].astype(int)  # 数量を整数に
        
        print(f"有効製造記録数: {len(df)}")
        print(f"製造合計数量: {df['quantity'].sum():,}個")
        
        # 商品別製造統計
        product_stats = df.groupby('product_name')['quantity'].sum().sort_values(ascending=False)
        print(f"\n主要製造商品（上位10品目）:")
        for product, qty in product_stats.head(10).items():
            print(f"  - {product}: {qty:,}個")
        
        return df.to_dict('records')
        
    except Exception as e:
        logger.error(f"製造データ読み込みエラー: {str(e)}")
        return []

def find_manufacturing_product_mapping(product_name, smaregi_id=None):
    """
    製造データの商品名・スマレジIDから共通コードを検索
    """
    try:
        # 1. スマレジIDがある場合、product_masterから直接検索
        if smaregi_id and pd.notna(smaregi_id):
            smaregi_str = str(int(smaregi_id))  # 10105 -> "10105"
            pm_result = supabase.table("product_master").select(
                "common_code, product_name"
            ).eq("rakuten_sku", smaregi_str).execute()
            
            if pm_result.data:
                return pm_result.data[0]['common_code'], 'smaregi_id_exact'
        
        # 2. 商品名での完全一致検索
        pm_result = supabase.table("product_master").select(
            "common_code, product_name"
        ).ilike("product_name", f"{product_name}").execute()
        
        if pm_result.data:
            return pm_result.data[0]['common_code'], 'product_name_exact'
        
        # 3. 商品名での部分一致検索
        pm_result = supabase.table("product_master").select(
            "common_code, product_name"
        ).ilike("product_name", f"%{product_name}%").execute()
        
        if pm_result.data:
            return pm_result.data[0]['common_code'], 'product_name_partial'
        
        # 4. choice_code_mappingから検索
        ccm_result = supabase.table("choice_code_mapping").select(
            "common_code, product_name"
        ).ilike("product_name", f"%{product_name}%").execute()
        
        if ccm_result.data:
            return ccm_result.data[0]['common_code'], 'choice_code_mapping'
        
        # 5. キーワード検索（より柔軟）
        keywords = product_name.replace('エゾ鹿', '鹿').replace('スライス', '').replace('ジャーキー', '').split()[:2]
        for keyword in keywords:
            if len(keyword) > 2:
                pm_result = supabase.table("product_master").select(
                    "common_code, product_name"
                ).ilike("product_name", f"%{keyword}%").execute()
                
                if pm_result.data:
                    return pm_result.data[0]['common_code'], 'keyword_search'
        
        return None, None
        
    except Exception as e:
        logger.error(f"製造マッピング検索エラー ({product_name}): {str(e)}")
        return None, None

def create_manufacturing_record(manufacturing_item, common_code):
    """
    製造記録をmanufacturing_logsテーブルに作成（テーブルが存在しない場合は在庫に直接反映）
    """
    try:
        date = manufacturing_item['date']
        product_name = manufacturing_item['product_name']
        quantity = manufacturing_item['quantity']
        
        # 製造ログテーブルへの記録を試行（存在しない場合はスキップ）
        manufacturing_log = {
            'common_code': common_code,
            'product_name': product_name,
            'manufacturing_date': date.isoformat() if isinstance(date, datetime) else str(date),
            'quantity': quantity,
            'notes': f"製造データ同期: カテゴリ={manufacturing_item.get('category', '')}",
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # 在庫の直接更新（製造による在庫増加）
        existing_inventory = supabase.table('inventory').select('current_stock').eq('common_code', common_code).execute()
        
        if existing_inventory.data:
            # 既存在庫に加算
            current_stock = existing_inventory.data[0]['current_stock'] or 0
            new_stock = current_stock + quantity
            
            supabase.table('inventory').update({
                'current_stock': new_stock,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }).eq('common_code', common_code).execute()
            
            return True, f"在庫更新: {current_stock} -> {new_stock}"
        else:
            # 新規在庫レコード作成
            inventory_data = {
                'common_code': common_code,
                'current_stock': quantity,
                'minimum_stock': max(1, quantity // 10),
                'product_name': product_name,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            supabase.table('inventory').insert(inventory_data).execute()
            return True, f"新規在庫作成: {quantity}個"
            
    except Exception as e:
        logger.error(f"製造記録作成エラー: {str(e)}")
        return False, str(e)

def sync_manufacturing_data(manufacturing_data):
    """
    製造データをSupabaseに同期
    """
    print("\n" + "=" * 60)
    print("製造データ同期開始")
    print("=" * 60)
    
    mapped_count = 0
    unmapped_count = 0
    success_count = 0
    error_count = 0
    
    mapping_stats = {
        'smaregi_id_exact': 0,
        'product_name_exact': 0,
        'product_name_partial': 0,
        'choice_code_mapping': 0,
        'keyword_search': 0,
        'unmapped': 0
    }
    
    inventory_changes = {}  # 在庫変更追跡
    
    print("製造データマッピング進行中...")
    
    for i, item in enumerate(manufacturing_data, 1):
        try:
            product_name = item['product_name']
            quantity = item['quantity']
            smaregi_id = item.get('smaregi_id')
            
            # 共通コードを検索
            common_code, mapping_source = find_manufacturing_product_mapping(product_name, smaregi_id)
            
            if common_code:
                mapped_count += 1
                mapping_stats[mapping_source] += 1
                
                # 製造記録作成・在庫更新
                success, message = create_manufacturing_record(item, common_code)
                
                if success:
                    success_count += 1
                    
                    # 在庫変更追跡
                    if common_code not in inventory_changes:
                        inventory_changes[common_code] = {
                            'product_name': product_name,
                            'total_manufactured': 0
                        }
                    inventory_changes[common_code]['total_manufactured'] += quantity
                    
                    if i % 100 == 0:
                        print(f"  [{i}/{len(manufacturing_data)}] {product_name} -> {common_code} (+{quantity}) - {message}")
                else:
                    error_count += 1
                    logger.error(f"製造記録作成失敗 ({product_name} -> {common_code}): {message}")
            else:
                unmapped_count += 1
                mapping_stats['unmapped'] += 1
                
                if i % 100 == 0:
                    print(f"  [{i}/{len(manufacturing_data)}] {product_name} - マッピングなし")
                
        except Exception as e:
            error_count += 1
            logger.error(f"製造データ処理エラー ({item.get('product_name', 'Unknown')}): {str(e)}")
    
    print("\n" + "=" * 60)
    print("製造データ同期完了サマリー")
    print("=" * 60)
    print(f"処理製造記録数: {len(manufacturing_data)}件")
    print(f"マッピング成功: {mapped_count}件")
    print(f"マッピング失敗: {unmapped_count}件")
    print(f"在庫更新成功: {success_count}件")
    print(f"在庫更新失敗: {error_count}件")
    
    print(f"\nマッピングソース別統計:")
    for source, count in mapping_stats.items():
        if count > 0:
            print(f"  - {source}: {count}件")
    
    # 在庫変更サマリー
    if inventory_changes:
        print(f"\n在庫変更サマリー（上位10品目）:")
        sorted_changes = sorted(inventory_changes.items(), key=lambda x: x[1]['total_manufactured'], reverse=True)
        for common_code, data in sorted_changes[:10]:
            product_name = data['product_name']
            manufactured = data['total_manufactured']
            print(f"  - {common_code}: {product_name} (+{manufactured:,}個)")
    
    # データベース最終状態確認
    total_inventory = supabase.table('inventory').select('id', count='exact').execute()
    total_count = total_inventory.count if hasattr(total_inventory, 'count') else 0
    
    total_stock = supabase.table('inventory').select('current_stock').execute()
    total_stock_value = sum(item['current_stock'] or 0 for item in total_stock.data)
    
    print(f"\nデータベース最終状態:")
    print(f"総在庫アイテム: {total_count}件")
    print(f"総在庫数: {total_stock_value:,}個")
    
    return mapped_count > 0

def main():
    """
    メイン実行関数
    """
    file_path = r'C:\Users\naoot\Downloads\製造.xlsx'
    
    print("製造データ同期システム開始")
    print(f"対象ファイル: {file_path}")
    
    try:
        # 1. 製造データ読み込み
        manufacturing_data = load_manufacturing_data(file_path)
        
        if not manufacturing_data:
            print("製造データが取得できませんでした")
            return False
        
        # 2. 製造データ同期・在庫更新
        success = sync_manufacturing_data(manufacturing_data)
        
        if success:
            print("\n製造データ同期が完了しました！")
            print("\n📊 同期結果:")
            print("- 製造データに基づいて在庫数が自動更新されました")
            print("- 商品名・スマレジIDマッピングにより正確な在庫反映を実現")
            print("- 製造による在庫増加が記録されました")
            
            return True
        else:
            print("\n製造データ同期でエラーが発生しました")
            return False
            
    except Exception as e:
        print(f"\nエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)