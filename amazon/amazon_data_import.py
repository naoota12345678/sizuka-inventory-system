"""
Amazon データインポートスクリプト
CSVファイルからSupabaseにデータをインポート
"""

import pandas as pd
from supabase import create_client
import os
from datetime import datetime
from typing import Dict, List, Optional
import json

# Supabase設定
SUPABASE_URL = 'https://equrcpeifogdrxoldkpe.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

class AmazonDataImporter:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.product_cache = {}
        self.mapping_cache = {}
        
    def import_orders_from_csv(self, csv_path: str):
        """
        Amazon注文CSVファイルからデータをインポート
        
        Expected CSV columns:
        - amazon-order-id
        - purchase-date
        - order-status
        - fulfillment-channel
        - sales-channel
        - ship-city
        - ship-state
        - ship-postal-code
        - ship-country
        - item-price
        - currency
        """
        print(f"CSVファイル読み込み中: {csv_path}")
        
        try:
            # CSVファイル読み込み
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            
            # カラム名を正規化
            df.columns = df.columns.str.strip().str.lower().str.replace('-', '_')
            
            total_orders = len(df)
            success_count = 0
            error_count = 0
            
            for _, row in df.iterrows():
                try:
                    # 注文データ準備
                    order_data = {
                        'order_id': str(row.get('amazon_order_id', '')),
                        'purchase_date': self._parse_date(row.get('purchase_date')),
                        'order_date': self._parse_date(row.get('purchase_date'))[:10] if row.get('purchase_date') else None,
                        'order_status': row.get('order_status', ''),
                        'fulfillment_channel': row.get('fulfillment_channel', ''),
                        'sales_channel': row.get('sales_channel', ''),
                        'ship_city': row.get('ship_city', ''),
                        'ship_state': row.get('ship_state', ''),
                        'ship_postal_code': str(row.get('ship_postal_code', '')),
                        'ship_country': row.get('ship_country', ''),
                        'total_amount': float(row.get('item_price', 0)) if pd.notna(row.get('item_price')) else 0,
                        'currency': row.get('currency', 'JPY')
                    }
                    
                    # 注文をupsert
                    self.supabase.table('amz_orders').upsert(
                        order_data,
                        on_conflict='order_id'
                    ).execute()
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"注文処理エラー: {row.get('amazon_order_id', 'Unknown')}: {e}")
                    error_count += 1
            
            print(f"\n✅ インポート完了:")
            print(f"  総件数: {total_orders}")
            print(f"  成功: {success_count}")
            print(f"  エラー: {error_count}")
            
        except Exception as e:
            print(f"CSVファイル読み込みエラー: {e}")
            
    def import_order_items_from_csv(self, csv_path: str):
        """
        Amazon注文商品詳細CSVファイルからデータをインポート
        
        Expected CSV columns:
        - amazon-order-id
        - order-item-id
        - asin
        - sku
        - product-name
        - quantity-ordered
        - item-price
        - item-tax
        - shipping-price
        - shipping-tax
        - promotion-discount
        """
        print(f"注文商品CSVファイル読み込み中: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            df.columns = df.columns.str.strip().str.lower().str.replace('-', '_')
            
            total_items = len(df)
            success_count = 0
            error_count = 0
            
            for _, row in df.iterrows():
                try:
                    item_data = {
                        'order_id': str(row.get('amazon_order_id', '')),
                        'order_item_id': str(row.get('order_item_id', '')),
                        'asin': str(row.get('asin', '')),
                        'sku': str(row.get('sku', '')),
                        'product_name': row.get('product_name', ''),
                        'quantity': int(row.get('quantity_ordered', 1)) if pd.notna(row.get('quantity_ordered')) else 1,
                        'item_price': float(row.get('item_price', 0)) if pd.notna(row.get('item_price')) else 0,
                        'item_tax': float(row.get('item_tax', 0)) if pd.notna(row.get('item_tax')) else 0,
                        'shipping_price': float(row.get('shipping_price', 0)) if pd.notna(row.get('shipping_price')) else 0,
                        'shipping_tax': float(row.get('shipping_tax', 0)) if pd.notna(row.get('shipping_tax')) else 0,
                        'promotion_discount': float(row.get('promotion_discount', 0)) if pd.notna(row.get('promotion_discount')) else 0
                    }
                    
                    # 注文商品をupsert
                    self.supabase.table('amz_order_items').upsert(
                        item_data,
                        on_conflict='order_item_id'
                    ).execute()
                    
                    # 商品マスタも更新
                    self._update_product_master(
                        asin=item_data['asin'],
                        sku=item_data['sku'],
                        product_name=item_data['product_name']
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"商品処理エラー: {row.get('order_item_id', 'Unknown')}: {e}")
                    error_count += 1
            
            print(f"\n✅ 商品インポート完了:")
            print(f"  総件数: {total_items}")
            print(f"  成功: {success_count}")
            print(f"  エラー: {error_count}")
            
        except Exception as e:
            print(f"CSVファイル読み込みエラー: {e}")
    
    def _update_product_master(self, asin: str, sku: str, product_name: str):
        """商品マスタを更新"""
        try:
            product_data = {
                'asin': asin,
                'sku': sku,
                'product_name': product_name
            }
            
            self.supabase.table('amz_product_master').upsert(
                product_data,
                on_conflict='asin'
            ).execute()
            
        except Exception as e:
            print(f"商品マスタ更新エラー: {asin}: {e}")
    
    def _parse_date(self, date_str):
        """日付文字列をパース"""
        if pd.isna(date_str):
            return None
            
        try:
            # Amazon形式: 2024-08-01T09:30:00+00:00
            if 'T' in str(date_str):
                return date_str
            # 通常の日付形式
            else:
                return datetime.strptime(str(date_str), '%Y-%m-%d').isoformat()
        except:
            return None
    
    def create_sample_csv(self):
        """サンプルCSVファイルを作成"""
        
        # 注文サンプル
        orders_sample = pd.DataFrame({
            'amazon-order-id': ['123-456789-0123456', '123-456789-0123457'],
            'purchase-date': ['2025-08-01T10:30:00+09:00', '2025-08-02T14:20:00+09:00'],
            'order-status': ['Shipped', 'Shipped'],
            'fulfillment-channel': ['Amazon', 'Merchant'],
            'sales-channel': ['Amazon.co.jp', 'Amazon.co.jp'],
            'ship-city': ['東京', '大阪'],
            'ship-state': ['東京都', '大阪府'],
            'ship-postal-code': ['100-0001', '530-0001'],
            'ship-country': ['JP', 'JP'],
            'item-price': [3000, 5000],
            'currency': ['JPY', 'JPY']
        })
        
        # 商品サンプル
        items_sample = pd.DataFrame({
            'amazon-order-id': ['123-456789-0123456', '123-456789-0123456', '123-456789-0123457'],
            'order-item-id': ['item-001', 'item-002', 'item-003'],
            'asin': ['B08ABC12345', 'B08DEF67890', 'B08GHI11111'],
            'sku': ['AMZ-SKU-001', 'AMZ-SKU-002', 'AMZ-SKU-003'],
            'product-name': ['ペット用品A', 'ペット用品B', 'ペット用品C'],
            'quantity-ordered': [2, 1, 3],
            'item-price': [1500, 1500, 5000],
            'item-tax': [150, 150, 500],
            'shipping-price': [500, 0, 600],
            'shipping-tax': [50, 0, 60],
            'promotion-discount': [0, 300, 0]
        })
        
        # CSVファイル保存
        orders_sample.to_csv('sample_amazon_orders.csv', index=False, encoding='utf-8-sig')
        items_sample.to_csv('sample_amazon_items.csv', index=False, encoding='utf-8-sig')
        
        print("✅ サンプルCSVファイルを作成しました:")
        print("  - sample_amazon_orders.csv")
        print("  - sample_amazon_items.csv")


def main():
    importer = AmazonDataImporter()
    
    print("Amazon データインポートツール")
    print("=" * 50)
    print("1. サンプルCSVファイルを作成")
    print("2. 注文データをインポート")
    print("3. 商品データをインポート")
    print("4. 両方インポート")
    
    choice = input("\n選択してください (1-4): ")
    
    if choice == '1':
        importer.create_sample_csv()
        
    elif choice == '2':
        csv_path = input("注文CSVファイルのパスを入力: ")
        if os.path.exists(csv_path):
            importer.import_orders_from_csv(csv_path)
        else:
            print(f"ファイルが見つかりません: {csv_path}")
            
    elif choice == '3':
        csv_path = input("商品CSVファイルのパスを入力: ")
        if os.path.exists(csv_path):
            importer.import_order_items_from_csv(csv_path)
        else:
            print(f"ファイルが見つかりません: {csv_path}")
            
    elif choice == '4':
        orders_csv = input("注文CSVファイルのパスを入力: ")
        items_csv = input("商品CSVファイルのパスを入力: ")
        
        if os.path.exists(orders_csv) and os.path.exists(items_csv):
            importer.import_orders_from_csv(orders_csv)
            importer.import_order_items_from_csv(items_csv)
        else:
            print("ファイルが見つかりません")


if __name__ == "__main__":
    main()