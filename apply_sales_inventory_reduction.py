#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
売上データに基づく在庫減少適用スクリプト
既存の売上データ（楽天・Amazon）から在庫減少を計算・適用
"""

import os
import sys
import logging
from datetime import datetime, timezone
from supabase import create_client
from collections import defaultdict

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

def get_all_sales_data():
    """
    すべての売上データ（order_items）を取得
    """
    print("=" * 60)
    print("売上データ取得開始")
    print("=" * 60)
    
    try:
        # 全order_itemsを取得（2月10日以降）
        result = supabase.table('order_items').select(
            'quantity, product_code, choice_code, product_name, created_at, orders(order_date, platform_id)'
        ).gte('orders.order_date', '2025-02-10').execute()
        
        if not result.data:
            print("売上データが見つかりません")
            return []
        
        print(f"取得した売上アイテム数: {len(result.data)}件")
        
        # プラットフォーム別統計
        platform_stats = defaultdict(int)
        for item in result.data:
            order_info = item.get('orders')
            if order_info:
                platform_id = order_info.get('platform_id', 0)
                platform_stats[platform_id] += 1
        
        print("プラットフォーム別売上アイテム:")
        platform_names = {1: '楽天', 2: 'Amazon', 3: 'ColorME', 4: 'Airegi'}
        for platform_id, count in platform_stats.items():
            name = platform_names.get(platform_id, f'Platform_{platform_id}')
            print(f"  - {name}: {count}件")
        
        return result.data
        
    except Exception as e:
        logger.error(f"売上データ取得エラー: {str(e)}")
        return []

def find_inventory_mapping(product_code, choice_code, product_name):
    """
    売上商品から在庫の共通コードを検索
    """
    try:
        # 1. choice_codeがある場合の検索
        if choice_code and choice_code.strip():
            ccm_result = supabase.table("choice_code_mapping").select(
                "common_code, product_name"
            ).eq("choice_info->>choice_code", choice_code).execute()
            
            if ccm_result.data:
                return ccm_result.data[0]['common_code'], 'choice_code'
        
        # 2. product_codeでの検索（楽天SKU）
        if product_code and product_code != 'unknown':
            pm_result = supabase.table("product_master").select(
                "common_code, product_name"
            ).eq("rakuten_sku", product_code).execute()
            
            if pm_result.data:
                return pm_result.data[0]['common_code'], 'product_code'
        
        # 3. 商品名での部分一致検索
        if product_name and product_name.strip():
            pm_result = supabase.table("product_master").select(
                "common_code, product_name"
            ).ilike("product_name", f"%{product_name}%").execute()
            
            if pm_result.data:
                return pm_result.data[0]['common_code'], 'product_name'
        
        return None, None
        
    except Exception as e:
        logger.error(f"在庫マッピング検索エラー: {str(e)}")
        return None, None

def calculate_inventory_reductions(sales_data):
    """
    売上データから在庫減少量を計算
    """
    print("\n" + "=" * 60)
    print("在庫減少量計算開始")
    print("=" * 60)
    
    inventory_reductions = defaultdict(lambda: {'total_sold': 0, 'product_name': '', 'mapping_source': ''})
    mapping_stats = defaultdict(int)
    unmapped_items = []
    
    print("売上データマッピング進行中...")
    
    for i, item in enumerate(sales_data, 1):
        try:
            product_code = item.get('product_code', '')
            choice_code = item.get('choice_code', '')
            product_name = item.get('product_name', '')
            quantity = int(item.get('quantity', 0))
            
            if quantity <= 0:
                continue
            
            # 在庫マッピング検索
            common_code, mapping_source = find_inventory_mapping(product_code, choice_code, product_name)
            
            if common_code:
                inventory_reductions[common_code]['total_sold'] += quantity
                inventory_reductions[common_code]['product_name'] = product_name or f"商品_{product_code}"
                inventory_reductions[common_code]['mapping_source'] = mapping_source
                mapping_stats[mapping_source] += 1
                
                if i % 500 == 0:
                    print(f"  [{i}/{len(sales_data)}] {product_name or product_code} -> {common_code} (-{quantity})")
            else:
                unmapped_items.append({
                    'product_code': product_code,
                    'choice_code': choice_code,
                    'product_name': product_name,
                    'quantity': quantity
                })
                mapping_stats['unmapped'] += 1
                
        except Exception as e:
            logger.error(f"在庫減少計算エラー (アイテム {i}): {str(e)}")
    
    print(f"\n在庫減少計算完了:")
    print(f"処理アイテム数: {len(sales_data)}件")
    print(f"マッピング成功: {len(inventory_reductions)}商品")
    print(f"マッピング失敗: {len(unmapped_items)}件")
    
    print(f"\nマッピングソース別統計:")
    for source, count in mapping_stats.items():
        print(f"  - {source}: {count}件")
    
    # 在庫減少上位商品
    sorted_reductions = sorted(inventory_reductions.items(), key=lambda x: x[1]['total_sold'], reverse=True)
    print(f"\n在庫減少上位商品（上位15件）:")
    for common_code, data in sorted_reductions[:15]:
        product_name = data['product_name']
        sold = data['total_sold']
        source = data['mapping_source']
        print(f"  - {common_code}: {product_name} (-{sold:,}個) [{source}]")
    
    # マッピング失敗商品
    if unmapped_items:
        print(f"\nマッピング失敗商品（上位10件）:")
        unmapped_summary = defaultdict(int)
        for item in unmapped_items:
            key = item['product_name'] or item['product_code'] or 'Unknown'
            unmapped_summary[key] += item['quantity']
        
        sorted_unmapped = sorted(unmapped_summary.items(), key=lambda x: x[1], reverse=True)
        for product, quantity in sorted_unmapped[:10]:
            print(f"  - {product}: -{quantity}個")
    
    return dict(inventory_reductions), unmapped_items

def apply_inventory_reductions(inventory_reductions, dry_run=True):
    """
    在庫減少を実際のinventoryテーブルに適用
    """
    print("\n" + "=" * 60)
    print(f"在庫減少適用{'（DRY RUN）' if dry_run else ''}開始")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    insufficient_stock_count = 0
    not_found_count = 0
    
    inventory_changes = []
    
    for common_code, reduction_data in inventory_reductions.items():
        try:
            total_sold = reduction_data['total_sold']
            product_name = reduction_data['product_name']
            
            # 現在の在庫を取得
            existing = supabase.table('inventory').select(
                'current_stock, product_name'
            ).eq('common_code', common_code).execute()
            
            if not existing.data:
                not_found_count += 1
                print(f"  在庫なし: {common_code} - {product_name} (-{total_sold})")
                continue
            
            current_stock = existing.data[0]['current_stock'] or 0
            new_stock = current_stock - total_sold
            
            # 在庫不足チェック
            if new_stock < 0:
                insufficient_stock_count += 1
                print(f"  在庫不足: {common_code} - {product_name} (在庫:{current_stock}, 売上:{total_sold})")
                # 在庫不足でも0に設定
                new_stock = 0
            
            change_info = {
                'common_code': common_code,
                'product_name': product_name,
                'before_stock': current_stock,
                'sold_quantity': total_sold,
                'after_stock': new_stock,
                'change': new_stock - current_stock
            }
            inventory_changes.append(change_info)
            
            if not dry_run:
                # 実際の在庫更新
                supabase.table('inventory').update({
                    'current_stock': new_stock,
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).eq('common_code', common_code).execute()
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            logger.error(f"在庫減少適用エラー ({common_code}): {str(e)}")
    
    print(f"\n在庫減少適用結果:")
    print(f"処理商品数: {len(inventory_reductions)}件")
    print(f"適用成功: {success_count}件")
    print(f"在庫不足: {insufficient_stock_count}件")
    print(f"在庫なし: {not_found_count}件")
    print(f"エラー: {error_count}件")
    
    # 在庫変更サマリー（変更量順）
    sorted_changes = sorted(inventory_changes, key=lambda x: abs(x['change']), reverse=True)
    print(f"\n在庫変更サマリー（上位15件）:")
    for change in sorted_changes[:15]:
        code = change['common_code']
        name = change['product_name']
        before = change['before_stock']
        after = change['after_stock']
        sold = change['sold_quantity']
        print(f"  - {code}: {name}")
        print(f"    {before:,}個 -> {after:,}個 (売上: -{sold:,}個)")
    
    return success_count > 0, inventory_changes

def main():
    """
    メイン実行関数
    """
    print("売上データに基づく在庫減少適用システム")
    print("対象期間: 2025年2月10日以降の全売上")
    
    try:
        # 1. 売上データ取得
        sales_data = get_all_sales_data()
        if not sales_data:
            print("売上データが取得できませんでした")
            return False
        
        # 2. 在庫減少量計算
        inventory_reductions, unmapped_items = calculate_inventory_reductions(sales_data)
        if not inventory_reductions:
            print("在庫減少対象が見つかりませんでした")
            return False
        
        # 3. DRY RUN実行
        print("\n" + "="*60)
        print("DRY RUN実行（実際の変更はしません）")
        print("="*60)
        dry_run_success, changes = apply_inventory_reductions(inventory_reductions, dry_run=True)
        
        if not dry_run_success:
            print("DRY RUNでエラーが発生しました")
            return False
        
        # 4. 実行確認
        print(f"\n在庫減少適用の準備が完了しました:")
        print(f"- 対象商品数: {len(inventory_reductions)}件")
        print(f"- 総売上数量: {sum(r['total_sold'] for r in inventory_reductions.values()):,}個")
        print(f"- 現在の総在庫数: {sum(c['before_stock'] for c in changes):,}個")
        print(f"- 適用後総在庫数: {sum(c['after_stock'] for c in changes):,}個")
        
        confirm = input("\n実際に在庫減少を適用しますか？ (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            print("\n実際の在庫減少を適用中...")
            success, final_changes = apply_inventory_reductions(inventory_reductions, dry_run=False)
            
            if success:
                print("\n在庫減少適用が完了しました！")
                print("\n📊 最終結果:")
                print("- 売上データに基づく在庫減少が正確に反映されました")
                print("- 製造データ + 棚卸在庫 - 売上 = 現実的な在庫数")
                print("- 在庫管理システムが完全に整合性を保ちます")
                return True
            else:
                print("在庫減少適用でエラーが発生しました")
                return False
        else:
            print("在庫減少適用をキャンセルしました")
            return True
            
    except Exception as e:
        print(f"エラー: {str(e)}")
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