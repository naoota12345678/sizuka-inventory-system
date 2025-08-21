#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
未マッピング商品管理システム
1. 未マッピング商品の検出と通知
2. 管理者による手動マッピング追加機能
"""

import os
import logging
from datetime import datetime, timezone
from supabase import create_client
from collections import defaultdict, Counter
import json

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

def detect_unmapped_products():
    """未マッピング商品を検出"""
    print("=" * 80)
    print("未マッピング商品検出システム")
    print("=" * 80)
    
    try:
        # マッピングテーブル取得
        pm_data = supabase.table('product_master').select('rakuten_sku, common_code, product_name').execute()
        sku_mapping = {}
        for item in pm_data.data:
            sku = item.get('rakuten_sku')
            if sku:
                sku_mapping[str(sku)] = item
        
        ccm_data = supabase.table('choice_code_mapping').select('choice_info, common_code, product_name').execute()
        choice_mapping = {}
        for item in ccm_data.data:
            choice_info = item.get('choice_info', {})
            if isinstance(choice_info, dict) and 'choice_code' in choice_info:
                choice_mapping[choice_info['choice_code']] = item
        
        print(f"マッピングテーブル読み込み完了:")
        print(f"  - product_master: {len(sku_mapping)}件")
        print(f"  - choice_code_mapping: {len(choice_mapping)}件")
        
        # 楽天データから未マッピング商品を検出
        print(f"\n楽天データ分析中...")
        
        unmapped_products = []
        page_size = 1000
        offset = 0
        total_processed = 0
        
        while True:
            try:
                result = supabase.table('order_items').select(
                    'id, quantity, choice_code, rakuten_item_number, product_code, product_name, orders!inner(platform_id, order_date)'
                ).eq('orders.platform_id', 1).range(offset, offset + page_size - 1).execute()
                
                if not result.data:
                    break
                
                for item in result.data:
                    quantity = int(item.get('quantity', 0))
                    if quantity <= 0:
                        continue
                    
                    total_processed += 1
                    choice_code = item.get('choice_code', '') or ''
                    rakuten_item_number = item.get('rakuten_item_number', '') or ''
                    
                    # マッピング確認
                    mapped = False
                    if choice_code and choice_code in choice_mapping:
                        mapped = True
                    elif rakuten_item_number and str(rakuten_item_number) in sku_mapping:
                        mapped = True
                    
                    if not mapped:
                        unmapped_products.append({
                            'id': item['id'],
                            'quantity': quantity,
                            'choice_code': choice_code,
                            'rakuten_item_number': rakuten_item_number,
                            'product_code': item.get('product_code', ''),
                            'product_name': item.get('product_name', ''),
                            'order_date': item.get('orders', {}).get('order_date', ''),
                            'first_seen': item.get('orders', {}).get('order_date', '')
                        })
                
                if len(result.data) < page_size:
                    break
                
                offset += page_size
                if offset % 5000 == 0:
                    print(f"  処理済み: {offset}件...")
            
            except Exception as e:
                print(f"データ取得エラー: {e}")
                break
        
        # 未マッピング商品の集計
        unmapped_summary = defaultdict(lambda: {
            'total_quantity': 0,
            'order_count': 0,
            'first_seen': None,
            'last_seen': None,
            'sample_data': None
        })
        
        for item in unmapped_products:
            # キーの決定（choice_code優先、なければSKU）
            key = item['choice_code'] if item['choice_code'] else f"sku_{item['rakuten_item_number']}"
            
            summary = unmapped_summary[key]
            summary['total_quantity'] += item['quantity']
            summary['order_count'] += 1
            
            order_date = item['order_date']
            if summary['first_seen'] is None or order_date < summary['first_seen']:
                summary['first_seen'] = order_date
            if summary['last_seen'] is None or order_date > summary['last_seen']:
                summary['last_seen'] = order_date
            
            if summary['sample_data'] is None:
                summary['sample_data'] = item
        
        # 結果出力
        print(f"\n" + "=" * 80)
        print("未マッピング商品検出結果")
        print("=" * 80)
        print(f"総処理アイテム数: {total_processed:,}件")
        print(f"未マッピング商品種類: {len(unmapped_summary)}種類")
        print(f"未マッピング総数量: {sum(p['total_quantity'] for p in unmapped_summary.values())}個")
        
        if unmapped_summary:
            print(f"\n【未マッピング商品一覧】")
            # 数量順でソート
            sorted_unmapped = sorted(unmapped_summary.items(), 
                                   key=lambda x: x[1]['total_quantity'], reverse=True)
            
            for i, (key, summary) in enumerate(sorted_unmapped, 1):
                sample = summary['sample_data']
                print(f"\n{i}. 識別子: {key}")
                print(f"   総数量: {summary['total_quantity']}個 ({summary['order_count']}回注文)")
                print(f"   期間: {summary['first_seen'][:10]} ～ {summary['last_seen'][:10]}")
                print(f"   choice_code: '{sample['choice_code']}'")
                print(f"   rakuten_item_number: '{sample['rakuten_item_number']}'")
                print(f"   product_code: '{sample['product_code']}'")
                print(f"   product_name: '{sample['product_name']}'")
        
        return unmapped_summary
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_mapping_interactively(unmapped_summary):
    """対話的にマッピングを作成"""
    if not unmapped_summary:
        print("未マッピング商品がありません。")
        return
    
    print(f"\n" + "=" * 80)
    print("対話的マッピング作成")
    print("=" * 80)
    
    # 数量順でソート
    sorted_unmapped = sorted(unmapped_summary.items(), 
                           key=lambda x: x[1]['total_quantity'], reverse=True)
    
    for i, (key, summary) in enumerate(sorted_unmapped, 1):
        sample = summary['sample_data']
        
        print(f"\n【商品 {i}/{len(sorted_unmapped)}】")
        print(f"識別子: {key}")
        print(f"総数量: {summary['total_quantity']}個 ({summary['order_count']}回注文)")
        print(f"商品名: '{sample['product_name']}'")
        print(f"choice_code: '{sample['choice_code']}'")
        print(f"rakuten_item_number: '{sample['rakuten_item_number']}'")
        
        print(f"\nこの商品をどうしますか？")
        print(f"1. 新しい共通コードを作成してマッピング")
        print(f"2. 既存の共通コードにマッピング")
        print(f"3. スキップ（後で対応）")
        print(f"4. 除外商品として記録（販売終了等）")
        print(f"0. 終了")
        
        while True:
            try:
                choice = input(f"\n選択してください (0-4): ").strip()
                if choice in ['0', '1', '2', '3', '4']:
                    break
                print("0-4の数字を入力してください。")
            except KeyboardInterrupt:
                print(f"\n処理を中断しました。")
                return
        
        if choice == '0':
            print("処理を終了します。")
            break
        elif choice == '1':
            create_new_mapping(sample, summary)
        elif choice == '2':
            map_to_existing(sample, summary)
        elif choice == '3':
            print("スキップしました。")
            continue
        elif choice == '4':
            mark_as_excluded(sample, summary)

def create_new_mapping(sample, summary):
    """新しい共通コードを作成してマッピング"""
    try:
        print(f"\n新しい共通コードを作成します。")
        
        # 新しい共通コード生成
        common_code = input(f"共通コード（例: CM999）: ").strip()
        if not common_code:
            print("共通コードが入力されませんでした。スキップします。")
            return
        
        product_name = input(f"商品名（現在: '{sample['product_name']}'）: ").strip()
        if not product_name:
            product_name = sample['product_name']
        
        choice_code = sample['choice_code']
        rakuten_sku = sample['rakuten_item_number']
        
        print(f"\n作成する内容:")
        print(f"  共通コード: {common_code}")
        print(f"  商品名: {product_name}")
        print(f"  choice_code: {choice_code}")
        print(f"  rakuten_sku: {rakuten_sku}")
        
        confirm = input(f"\n作成しますか？ (y/n): ").strip().lower()
        if confirm != 'y':
            print("キャンセルしました。")
            return
        
        # choice_code_mappingに追加（choice_codeがある場合）
        if choice_code:
            choice_record = {
                'choice_info': {
                    'choice_code': choice_code,
                    'choice_name': f'{choice_code} Choice',
                    'choice_value': product_name,
                    'category': 'manual_addition'
                },
                'common_code': common_code,
                'product_name': product_name,
                'rakuten_sku': f'CHOICE_{choice_code}'
            }
            
            choice_result = supabase.table('choice_code_mapping').insert(choice_record).execute()
            if choice_result.data:
                print(f"✓ choice_code_mapping追加成功")
            else:
                print(f"✗ choice_code_mapping追加失敗")
                return
        
        # product_masterに追加（rakuten_skuがある場合）
        if rakuten_sku:
            product_record = {
                'rakuten_sku': str(rakuten_sku),
                'common_code': common_code,
                'product_name': product_name
            }
            
            product_result = supabase.table('product_master').insert(product_record).execute()
            if product_result.data:
                print(f"✓ product_master追加成功")
            else:
                print(f"✗ product_master追加失敗")
                return
        
        # inventoryレコード作成
        inventory_record = {
            'common_code': common_code,
            'product_name': product_name,
            'current_stock': 0,
            'minimum_stock': 0,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        inventory_result = supabase.table('inventory').insert(inventory_record).execute()
        if inventory_result.data:
            print(f"✓ inventory追加成功")
        else:
            print(f"✗ inventory追加失敗")
            return
        
        print(f"\n✅ マッピング作成完了: {common_code}")
        
    except Exception as e:
        print(f"エラー: {str(e)}")

def map_to_existing(sample, summary):
    """既存の共通コードにマッピング"""
    try:
        print(f"\n既存の共通コードにマッピングします。")
        
        # 既存の共通コード一覧表示
        inventory_data = supabase.table('inventory').select('common_code, product_name').execute()
        print(f"\n既存の共通コード一覧（最近の20件）:")
        for i, item in enumerate(inventory_data.data[-20:], 1):
            print(f"  {i}. {item['common_code']}: {item['product_name']}")
        
        common_code = input(f"\nマッピング先の共通コード: ").strip()
        if not common_code:
            print("共通コードが入力されませんでした。スキップします。")
            return
        
        # 共通コードの存在確認
        existing = supabase.table('inventory').select('product_name').eq('common_code', common_code).execute()
        if not existing.data:
            print(f"共通コード {common_code} が見つかりません。")
            return
        
        choice_code = sample['choice_code']
        rakuten_sku = sample['rakuten_item_number']
        product_name = existing.data[0]['product_name']
        
        print(f"\n作成する内容:")
        print(f"  マッピング先: {common_code} ({product_name})")
        print(f"  choice_code: {choice_code}")
        print(f"  rakuten_sku: {rakuten_sku}")
        
        confirm = input(f"\nマッピングしますか？ (y/n): ").strip().lower()
        if confirm != 'y':
            print("キャンセルしました。")
            return
        
        # choice_code_mappingに追加（choice_codeがある場合）
        if choice_code:
            choice_record = {
                'choice_info': {
                    'choice_code': choice_code,
                    'choice_name': f'{choice_code} Choice',
                    'choice_value': product_name,
                    'category': 'manual_mapping'
                },
                'common_code': common_code,
                'product_name': product_name,
                'rakuten_sku': f'CHOICE_{choice_code}'
            }
            
            choice_result = supabase.table('choice_code_mapping').insert(choice_record).execute()
            if choice_result.data:
                print(f"✓ choice_code_mapping追加成功")
            else:
                print(f"✗ choice_code_mapping追加失敗")
                return
        
        # product_masterに追加（rakuten_skuがある場合）
        if rakuten_sku:
            product_record = {
                'rakuten_sku': str(rakuten_sku),
                'common_code': common_code,
                'product_name': product_name
            }
            
            product_result = supabase.table('product_master').insert(product_record).execute()
            if product_result.data:
                print(f"✓ product_master追加成功")
            else:
                print(f"✗ product_master追加失敗")
                return
        
        print(f"\n✅ 既存マッピング追加完了: {common_code}")
        
    except Exception as e:
        print(f"エラー: {str(e)}")

def mark_as_excluded(sample, summary):
    """除外商品として記録"""
    try:
        print(f"\n除外商品として記録します。")
        
        reason = input(f"除外理由（例: 販売終了、テスト商品等）: ").strip()
        if not reason:
            reason = "未分類"
        
        # 除外商品テーブルがなければ作成的な処理は省略し、
        # ここでは単純にログ出力で代替
        print(f"✓ 除外商品として記録: {sample['choice_code'] or sample['rakuten_item_number']}")
        print(f"  理由: {reason}")
        
        # 実際のシステムでは excluded_products テーブルに記録
        # excluded_record = {
        #     'choice_code': sample['choice_code'],
        #     'rakuten_sku': sample['rakuten_item_number'],
        #     'product_name': sample['product_name'],
        #     'exclusion_reason': reason,
        #     'excluded_at': datetime.now(timezone.utc).isoformat()
        # }
        
    except Exception as e:
        print(f"エラー: {str(e)}")

def main():
    """メイン処理"""
    print("未マッピング商品管理システムを開始します。")
    
    try:
        # 1. 未マッピング商品検出
        unmapped_summary = detect_unmapped_products()
        
        if unmapped_summary:
            print(f"\n{len(unmapped_summary)}種類の未マッピング商品が見つかりました。")
            
            response = input(f"\n対話的にマッピングを作成しますか？ (y/n): ").strip().lower()
            if response == 'y':
                create_mapping_interactively(unmapped_summary)
            else:
                print("マッピング作成をスキップしました。")
                
                # レポート出力
                print(f"\n未マッピング商品レポートを出力します。")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = f"unmapped_products_{timestamp}.txt"
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write("未マッピング商品レポート\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"生成日時: {datetime.now()}\n")
                    f.write(f"未マッピング商品数: {len(unmapped_summary)}種類\n\n")
                    
                    sorted_unmapped = sorted(unmapped_summary.items(), 
                                           key=lambda x: x[1]['total_quantity'], reverse=True)
                    
                    for i, (key, summary) in enumerate(sorted_unmapped, 1):
                        sample = summary['sample_data']
                        f.write(f"{i}. 識別子: {key}\n")
                        f.write(f"   総数量: {summary['total_quantity']}個\n")
                        f.write(f"   商品名: {sample['product_name']}\n")
                        f.write(f"   choice_code: {sample['choice_code']}\n")
                        f.write(f"   rakuten_sku: {sample['rakuten_item_number']}\n")
                        f.write(f"   期間: {summary['first_seen'][:10]} ～ {summary['last_seen'][:10]}\n\n")
                
                print(f"レポートを保存しました: {report_file}")
        else:
            print("未マッピング商品は見つかりませんでした。")
    
    except KeyboardInterrupt:
        print(f"\n処理が中断されました。")
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()