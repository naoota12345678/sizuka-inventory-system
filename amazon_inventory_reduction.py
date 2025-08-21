#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazonデータ専用在庫減少処理
platform_id=2（Amazon）のデータをASINコードでマッピング
"""

import os
import sys
import logging
from datetime import datetime, timezone
from supabase import create_client
from collections import defaultdict
import time

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

def get_amazon_only_sales_data():
    """
    Amazonデータのみを取得（platform_id=2のorder_items）
    """
    print("Amazonデータのみを取得中...")
    
    all_amazon_data = []
    page_size = 1000
    offset = 0
    
    while True:
        try:
            # Amazonデータのみ取得（orders.platform_id = 2）
            result = supabase.table('order_items').select(
                'quantity, product_code, choice_code, product_name, rakuten_item_number, orders!inner(platform_id)'
            ).eq('orders.platform_id', 2).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
            
            all_amazon_data.extend(result.data)
            print(f"  取得済み: {len(all_amazon_data)}件 (今回: {len(result.data)}件)")
            
            if len(result.data) < page_size:
                break
            
            offset += page_size
            time.sleep(0.1)
            
        except Exception as e:
            print(f"データ取得エラー (offset: {offset}): {str(e)}")
            break
    
    print(f"Amazonデータ取得完了: {len(all_amazon_data)}件")
    return all_amazon_data

def create_amazon_asin_mapping_table():
    """
    Amazon ASIN→共通コードマッピングテーブルの作成
    """
    print("Amazon ASIN マッピングテーブルを確認中...")
    
    try:
        # amazon_product_masterテーブルが存在するか確認
        existing_table = supabase.table('amazon_product_master').select('asin, common_code, product_name').limit(1).execute()
        print(f"amazon_product_masterテーブル存在: {len(existing_table.data)}件確認")
        return True
        
    except Exception as e:
        print(f"amazon_product_masterテーブルが存在しません: {str(e)}")
        print("新規でAmazon商品マッピングを作成する必要があります")
        return False

def analyze_amazon_unmapped_data():
    """
    Amazon未マッピングデータの分析
    """
    print("=" * 60)
    print("Amazon未マッピングデータ分析開始")
    print("=" * 60)
    
    try:
        # Step 1: 既存のAmazon ASINマッピング取得（存在する場合）
        print("Step 1: 既存Amazon ASINマッピング取得中...")
        
        asin_mapping = {}
        try:
            asin_data = supabase.table('amazon_product_master').select('asin, common_code, product_name').execute()
            for item in asin_data.data:
                asin = item.get('asin')
                if asin:
                    asin_mapping[asin] = item['common_code']
            print(f"  - 既存ASINマッピング: {len(asin_mapping)}件")
        except:
            print(f"  - amazon_product_masterテーブル未作成、新規作成が必要")
        
        # Step 2: Amazonデータ全件取得
        print("\nStep 2: Amazonデータ取得中...")
        amazon_sales_data = get_amazon_only_sales_data()
        
        # Step 3: Amazon未マッピング分析
        print("\nStep 3: Amazon未マッピング分析中...")
        
        asin_stats = defaultdict(int)
        product_name_stats = defaultdict(set)
        
        for item in amazon_sales_data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            asin = item.get('product_code', '')  # Amazonではproduct_codeがASIN
            product_name = item.get('product_name', '')
            
            if asin:
                asin_stats[asin] += quantity
                if product_name:
                    product_name_stats[asin].add(product_name)
        
        print(f"  - ユニークASIN数: {len(asin_stats)}件")
        print(f"  - Amazon売上アイテム数: {len(amazon_sales_data)}件")
        
        # マッピング状況確認
        mapped_count = 0
        unmapped_asins = {}
        
        for asin, total_qty in asin_stats.items():
            if asin in asin_mapping:
                mapped_count += 1
            else:
                # 商品名の統一
                product_names = list(product_name_stats[asin])
                primary_name = product_names[0] if product_names else f"Amazon商品_{asin}"
                unmapped_asins[asin] = {
                    'total_quantity': total_qty,
                    'product_name': primary_name
                }
        
        print(f"  - マッピング済みASIN: {mapped_count}件")
        print(f"  - 未マッピングASIN: {len(unmapped_asins)}件")
        
        # 未マッピングASIN詳細（上位10件）
        if unmapped_asins:
            print(f"\n未マッピングASIN（上位10件）:")
            sorted_unmapped = sorted(unmapped_asins.items(), key=lambda x: x[1]['total_quantity'], reverse=True)
            for asin, info in sorted_unmapped[:10]:
                print(f"  - ASIN {asin}: {info['total_quantity']}個 - {info['product_name'][:50]}")
        
        return True, {
            'total_asins': len(asin_stats),
            'amazon_items': len(amazon_sales_data),
            'mapped_asins': mapped_count,
            'unmapped_asins': unmapped_asins,
            'existing_mappings': len(asin_mapping)
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def create_amazon_complete_mappings(analysis_result):
    """
    Amazon用完全マッピングを作成
    """
    print(f"\n" + "=" * 60)
    print("Amazon完全マッピング作成開始")
    print("=" * 60)
    
    try:
        unmapped_asins = analysis_result['unmapped_asins']
        
        # Step 1: amazon_product_masterテーブルに新ASINマッピング作成
        print("Step 1: Amazon ASIN用マッピング作成中...")
        
        new_asin_mappings = []
        base_code = 800  # CM800番台をAmazon用に使用
        
        for asin, info in unmapped_asins.items():
            new_common_code = f"CM{base_code:03d}"
            
            new_mapping = {
                'asin': asin,
                'common_code': new_common_code,
                'product_name': info['product_name'],
                'platform': 'amazon',
                'total_quantity': info['total_quantity']
            }
            
            new_asin_mappings.append(new_mapping)
            base_code += 1
        
        # amazon_product_masterテーブルが存在しない場合は、product_masterに追加
        if new_asin_mappings:
            print(f"product_masterに{len(new_asin_mappings)}件のAmazon ASIN追加中...")
            
            # Amazon用マッピングをproduct_masterに格納（rakuten_skuフィールドにASINを格納）
            pm_mappings = []
            for mapping in new_asin_mappings:
                pm_mapping = {
                    'common_code': mapping['common_code'],
                    'product_name': f"[Amazon] {mapping['product_name']}",
                    'rakuten_sku': mapping['asin']  # ASINをrakuten_skuフィールドに格納
                }
                pm_mappings.append(pm_mapping)
            
            # バッチ挿入
            batch_size = 50
            inserted_count = 0
            for i in range(0, len(pm_mappings), batch_size):
                batch = pm_mappings[i:i + batch_size]
                try:
                    supabase.table('product_master').insert(batch).execute()
                    inserted_count += len(batch)
                    print(f"  - 挿入完了: {inserted_count}/{len(pm_mappings)}件")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  - バッチ挿入エラー: {str(e)}")
        
        print(f"Amazon完全マッピング作成完了: {len(new_asin_mappings)}件の新ASIN追加")
        
        return True, len(new_asin_mappings)
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, 0

def amazon_inventory_reduction():
    """
    Amazonデータの在庫減少処理
    """
    print("=" * 60)
    print("Amazon在庫減少処理開始")
    print("=" * 60)
    
    try:
        # Step 1: Amazon ASINマッピング取得（product_masterから）
        print("Step 1: Amazon ASINマッピングデータ取得中...")
        
        pm_data = supabase.table('product_master').select('rakuten_sku, common_code, product_name').execute()
        asin_mapping = {}
        for item in pm_data.data:
            sku = item.get('rakuten_sku')
            product_name = item.get('product_name', '')
            # Amazon ASINの特徴：B + 9文字の英数字
            if sku and (sku.startswith('B0') and len(sku) >= 10) or '[Amazon]' in product_name:
                asin_mapping[sku] = item['common_code']
        
        print(f"  - Amazon ASINマッピング: {len(asin_mapping)}件")
        
        # Step 2: Amazonデータ取得
        print("\nStep 2: Amazonデータ取得中...")
        amazon_sales_data = get_amazon_only_sales_data()
        
        # Step 3: 在庫減少量計算
        print("\nStep 3: Amazon在庫減少量計算中...")
        
        inventory_reductions = defaultdict(int)
        mapped_count = 0
        unmapped_count = 0
        unmapped_details = defaultdict(int)
        
        for item in amazon_sales_data:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                continue
            
            asin = item.get('product_code', '')  # Amazonではproduct_codeがASIN
            
            common_code = None
            
            if asin and asin in asin_mapping:
                common_code = asin_mapping[asin]
                mapped_count += 1
            else:
                unmapped_count += 1
                key = f"asin:{asin}"
                unmapped_details[key] += quantity
            
            if common_code:
                inventory_reductions[common_code] += quantity
        
        print(f"  - Amazon売上アイテム数: {len(amazon_sales_data)}件")
        print(f"  - マッピング成功: {mapped_count}件")
        print(f"  - マッピング失敗: {unmapped_count}件")
        print(f"  - 対象商品数: {len(inventory_reductions)}商品")
        
        # マッピング成功率計算
        success_rate = mapped_count / len(amazon_sales_data) * 100 if amazon_sales_data else 0
        print(f"  - Amazon ASINマッピング成功率: {success_rate:.1f}%")
        
        # 未マッピング詳細（上位5件のみ）
        if unmapped_details:
            print("\nAmazon未マッピング詳細（上位5件）:")
            sorted_unmapped = sorted(unmapped_details.items(), key=lambda x: x[1], reverse=True)
            for key, qty in sorted_unmapped[:5]:
                print(f"  - {key}: {qty}個")
        
        # Step 4: 在庫減少の適用
        print("\nStep 4: Amazon売上基準で在庫減少適用中...")
        
        success_count = 0
        total_reduced = 0
        reduction_details = []
        
        for common_code, reduction_amount in inventory_reductions.items():
            try:
                # 現在の在庫を取得
                existing = supabase.table('inventory').select('current_stock, product_name').eq('common_code', common_code).execute()
                
                if existing.data:
                    current_stock = existing.data[0]['current_stock'] or 0
                    product_name = existing.data[0].get('product_name', '')
                    new_stock = max(0, current_stock - reduction_amount)
                    
                    # 在庫更新
                    supabase.table('inventory').update({
                        'current_stock': new_stock,
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }).eq('common_code', common_code).execute()
                    
                    success_count += 1
                    total_reduced += reduction_amount
                    
                    reduction_details.append({
                        'common_code': common_code,
                        'product_name': product_name,
                        'before': current_stock,
                        'after': new_stock,
                        'reduction': reduction_amount
                    })
                    
                    if reduction_amount > 5:  # 大幅減少のみ表示
                        print(f"  - {common_code} ({product_name[:20]}): {current_stock} -> {new_stock} (-{reduction_amount})")
                
            except Exception as e:
                logger.error(f"在庫更新エラー ({common_code}): {str(e)}")
        
        print(f"\n" + "=" * 60)
        print("Amazon在庫減少処理完了")
        print("=" * 60)
        print(f"処理商品数: {success_count}件")
        print(f"総減少量: {total_reduced:,}個")
        
        # 最終在庫確認
        final_inventory = supabase.table('inventory').select('current_stock').execute()
        final_total = sum(item['current_stock'] or 0 for item in final_inventory.data)
        
        print(f"\n最終在庫数: {final_total:,}個")
        
        # 在庫減少商品詳細
        if reduction_details:
            print("\nAmazon売上による在庫減少（上位10件）:")
            sorted_reductions = sorted(reduction_details, key=lambda x: x['reduction'], reverse=True)
            for item in sorted_reductions[:10]:
                print(f"  - {item['common_code']}: {item['before']} -> {item['after']} (-{item['reduction']}) {item['product_name'][:30]}")
        
        print("\nAmazon在庫減少処理が完了しました！")
        
        return True, {
            'amazon_items': len(amazon_sales_data),
            'mapped_items': mapped_count,
            'unmapped_items': unmapped_count,
            'products_updated': success_count,
            'total_reduction': total_reduced,
            'final_inventory': final_total,
            'success_rate': success_rate
        }
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

if __name__ == "__main__":
    try:
        # Step 1: Amazon未マッピング分析
        print("Step 1: Amazon未マッピング分析開始")
        success, analysis = analyze_amazon_unmapped_data()
        
        if success:
            current_rate = analysis['mapped_asins'] / analysis['total_asins'] * 100 if analysis['total_asins'] > 0 else 0
            print(f"\n現在のAmazonマッピング状況:")
            print(f"  - 総ASIN数: {analysis['total_asins']:,}件")
            print(f"  - マッピング済み: {analysis['mapped_asins']:,}件")
            print(f"  - 未マッピング: {len(analysis['unmapped_asins']):,}件")
            print(f"  - マッピング成功率: {current_rate:.1f}%")
            
            # Step 2: 完全マッピング作成
            if analysis['unmapped_asins']:
                print(f"\n未マッピングASIN {len(analysis['unmapped_asins'])}件の完全マッピングを作成します。")
                print("100%マッピング達成のため自動実行します...")
                
                mapping_success, new_mappings = create_amazon_complete_mappings(analysis)
                
                if mapping_success:
                    print(f"\n[完了] {new_mappings}件の新ASINマッピング追加完了")
                    
                    # Step 3: Amazon在庫減少処理実行
                    print(f"\nStep 3: Amazon在庫減少処理実行中...")
                    reduction_success, results = amazon_inventory_reduction()
                    
                    if reduction_success:
                        print(f"\nAmazon処理サマリー:")
                        print(f"  - Amazon売上アイテム数: {results['amazon_items']:,}件")
                        print(f"  - マッピング成功率: {results['success_rate']:.1f}%")
                        print(f"  - 在庫更新商品数: {results['products_updated']}商品")
                        print(f"  - 総減少量: {results['total_reduction']:,}個")
                        print(f"  - 最終在庫数: {results['final_inventory']:,}個")
                    
                else:
                    print("マッピング作成でエラーが発生しました")
            else:
                print("\n既にすべてのASINがマッピング済みです")
                
                # マッピング完了済みの場合、直接在庫減少処理実行
                print(f"\nAmazon在庫減少処理を実行中...")
                reduction_success, results = amazon_inventory_reduction()
        else:
            print("分析でエラーが発生しました")
            
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)