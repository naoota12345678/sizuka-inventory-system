#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
棚卸在庫表から商品名マッピングで在庫初期値設定
2月10日時点の在庫数を設定
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

def load_inventory_from_excel(file_path):
    """
    棚卸在庫表Excelから商品名と在庫数を取得
    """
    print("=" * 60)
    print("棚卸在庫表読み込み開始")
    print("=" * 60)
    
    try:
        # 最初のシートを読み込み
        df = pd.read_excel(file_path, sheet_name=0)
        print(f"シート形状: {df.shape}")
        print(f"列名: {list(df.columns)}")
        
        inventory_items = []
        
        # 左半分のデータ処理
        if '商品名' in df.columns and '在庫数' in df.columns:
            left_valid = df[df['在庫数'].notna() & (df['在庫数'] >= 0)]
            print(f"左側有効データ数: {len(left_valid)}")
            
            for i, row in left_valid.iterrows():
                product_name = str(row['商品名']).strip()
                stock = int(row['在庫数']) if pd.notna(row['在庫数']) else 0
                
                if product_name and product_name != 'nan':
                    inventory_items.append({
                        'product_name': product_name,
                        'stock': stock,
                        'source': 'left'
                    })
        
        # 右半分のデータ処理
        if '商品名.1' in df.columns and '在庫数.1' in df.columns:
            right_valid = df[df['在庫数.1'].notna() & (df['在庫数.1'] >= 0)]
            print(f"右側有効データ数: {len(right_valid)}")
            
            for i, row in right_valid.iterrows():
                product_name = str(row['商品名.1']).strip() if pd.notna(row['商品名.1']) else ''
                stock = int(row['在庫数.1']) if pd.notna(row['在庫数.1']) else 0
                
                if product_name and product_name != 'nan':
                    inventory_items.append({
                        'product_name': product_name,
                        'stock': stock,
                        'source': 'right'
                    })
        
        print(f"総在庫アイテム数: {len(inventory_items)}")
        print(f"在庫総数: {sum(item['stock'] for item in inventory_items)}")
        
        return inventory_items
        
    except Exception as e:
        logger.error(f"Excelファイル読み込みエラー: {str(e)}")
        return []

def find_product_mapping(product_name):
    """
    商品名から共通コードを検索（複数のテーブルから）
    """
    try:
        # 1. product_masterから検索
        pm_result = supabase.table("product_master").select(
            "common_code, product_name"
        ).ilike("product_name", f"%{product_name}%").execute()
        
        if pm_result.data:
            return pm_result.data[0]['common_code'], 'product_master'
        
        # 2. choice_code_mappingから検索
        ccm_result = supabase.table("choice_code_mapping").select(
            "common_code, product_name"
        ).ilike("product_name", f"%{product_name}%").execute()
        
        if ccm_result.data:
            return ccm_result.data[0]['common_code'], 'choice_code_mapping'
        
        # 3. 部分一致検索（より柔軟）
        keywords = product_name.split()[:2]  # 最初の2単語で検索
        for keyword in keywords:
            if len(keyword) > 2:  # 短すぎるキーワードは除外
                pm_result = supabase.table("product_master").select(
                    "common_code, product_name"
                ).ilike("product_name", f"%{keyword}%").execute()
                
                if pm_result.data:
                    return pm_result.data[0]['common_code'], 'product_master_keyword'
        
        return None, None
        
    except Exception as e:
        logger.error(f"マッピング検索エラー ({product_name}): {str(e)}")
        return None, None

def setup_initial_inventory(inventory_items):
    """
    在庫初期値をinventoryテーブルに設定
    """
    print("\n" + "=" * 60)
    print("在庫初期値設定開始")
    print("=" * 60)
    
    mapped_count = 0
    unmapped_count = 0
    created_count = 0
    updated_count = 0
    
    mapping_stats = {
        'product_master': 0,
        'choice_code_mapping': 0,
        'product_master_keyword': 0,
        'unmapped': 0
    }
    
    print("マッピング進行中...")
    
    for i, item in enumerate(inventory_items, 1):
        product_name = item['product_name']
        stock = item['stock']
        
        try:
            # 共通コードを検索
            common_code, mapping_source = find_product_mapping(product_name)
            
            if common_code:
                mapped_count += 1
                mapping_stats[mapping_source] += 1
                
                # 既存在庫レコードをチェック
                existing = supabase.table('inventory').select('id').eq('common_code', common_code).execute()
                
                if existing.data:
                    # 既存レコードを更新
                    inventory_data = {
                        'current_stock': stock,
                        'minimum_stock': max(1, stock // 10),  # 在庫数の10%を最小在庫に
                        'product_name': product_name,
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }
                    
                    supabase.table('inventory').update(inventory_data).eq('common_code', common_code).execute()
                    updated_count += 1
                    
                    if i % 10 == 0:
                        print(f"  [{i}/{len(inventory_items)}] {product_name} -> {common_code} (更新)")
                else:
                    # 新規レコード作成
                    inventory_data = {
                        'common_code': common_code,
                        'current_stock': stock,
                        'minimum_stock': max(1, stock // 10),
                        'product_name': product_name,
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }
                    
                    supabase.table('inventory').insert(inventory_data).execute()
                    created_count += 1
                    
                    if i % 10 == 0:
                        print(f"  [{i}/{len(inventory_items)}] {product_name} -> {common_code} (新規)")
            else:
                unmapped_count += 1
                mapping_stats['unmapped'] += 1
                
                if i % 10 == 0:
                    print(f"  [{i}/{len(inventory_items)}] {product_name} -> マッピングなし")
                
        except Exception as e:
            logger.error(f"在庫設定エラー ({product_name}): {str(e)}")
    
    print("\n" + "=" * 60)
    print("在庫初期値設定完了サマリー")
    print("=" * 60)
    print(f"処理商品数: {len(inventory_items)}件")
    print(f"マッピング成功: {mapped_count}件")
    print(f"マッピング失敗: {unmapped_count}件")
    print(f"新規作成: {created_count}件")
    print(f"更新: {updated_count}件")
    
    print(f"\nマッピングソース別統計:")
    for source, count in mapping_stats.items():
        if count > 0:
            print(f"  - {source}: {count}件")
    
    # データベース最終状態確認
    total_inventory = supabase.table('inventory').select('id', count='exact').execute()
    total_count = total_inventory.count if hasattr(total_inventory, 'count') else 0
    
    print(f"\nデータベース内総在庫アイテム: {total_count}件")
    
    return mapped_count > 0

def main():
    """
    メイン実行関数
    """
    file_path = r'C:\Users\naoot\Downloads\棚卸在庫表 のコピー.xlsx'
    
    print("棚卸在庫表からの在庫初期値設定開始")
    print(f"対象ファイル: {file_path}")
    print(f"基準日: 2025年2月10日")
    
    try:
        # 1. Excelファイル読み込み
        inventory_items = load_inventory_from_excel(file_path)
        
        if not inventory_items:
            print("❌ 在庫データが取得できませんでした")
            return False
        
        # 2. 在庫初期値設定
        success = setup_initial_inventory(inventory_items)
        
        if success:
            print("\n在庫初期値設定が完了しました！")
            
            # 成功時の追加情報
            print("\n設定された在庫情報:")
            recent_inventory = supabase.table('inventory').select(
                'common_code, product_name, current_stock'
            ).order('last_updated', desc=True).limit(10).execute()
            
            if recent_inventory.data:
                print("最新の在庫設定 (上位10件):")
                for inv in recent_inventory.data:
                    code = inv['common_code']
                    name = inv['product_name']
                    stock = inv['current_stock']
                    print(f"  - {code}: {name} ({stock:,}個)")
            
            return True
        else:
            print("\n在庫初期値設定でエラーが発生しました")
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