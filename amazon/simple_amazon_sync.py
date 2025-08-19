#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Amazonシンプル同期
ASINから共通コードへのマッピング（すでにproduct_masterにある）
"""

import os
from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://equrcpeifogdrxoldkpe.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_common_code_by_asin(asin):
    """
    ASINから共通コードを取得
    product_masterテーブルのAmazon ASINカラムを使用
    """
    try:
        # product_masterからASINで検索
        result = supabase.table('product_master').select('common_code, product_name').eq('amazon_asin', asin).execute()
        
        if result.data:
            return result.data[0]['common_code'], result.data[0]['product_name']
        else:
            logger.warning(f"ASIN {asin} のマッピングが見つかりません")
            return None, None
            
    except Exception as e:
        logger.error(f"マッピング検索エラー: {str(e)}")
        return None, None

def process_amazon_order(order_data):
    """
    Amazon注文を処理
    """
    # 注文をordersテーブルに保存（platformをamazonに）
    order = {
        'order_number': order_data['amazon_order_id'],
        'order_date': order_data['purchase_date'],
        'platform': 'amazon',  # 重要: platformをamazonに設定
        'status': order_data.get('order_status', 'pending')
    }
    
    order_result = supabase.table('orders').insert(order).execute()
    order_id = order_result.data[0]['id']
    
    # 注文商品を処理
    for item in order_data['items']:
        asin = item['asin']
        
        # ASINから共通コードを取得
        common_code, product_name = get_common_code_by_asin(asin)
        
        if common_code:
            # order_itemsに保存
            order_item = {
                'order_id': order_id,
                'product_code': asin,  # ASINをproduct_codeとして保存
                'product_name': product_name or item.get('product_name', ''),
                'quantity': item['quantity'],
                'price': item['price'],
                'amazon_asin': asin  # Amazon ASIN用フィールド（必要なら）
            }
            
            supabase.table('order_items').insert(order_item).execute()
            
            # 在庫を減らす
            update_inventory(common_code, -item['quantity'])
            
            logger.info(f"Amazon注文処理: ASIN {asin} → 共通コード {common_code}")
        else:
            logger.warning(f"マッピングなし: ASIN {asin}")

def update_inventory(common_code, quantity_change):
    """
    在庫を更新
    """
    try:
        # 現在の在庫を取得
        current = supabase.table('inventory').select('current_stock').eq('common_code', common_code).execute()
        
        if current.data:
            new_stock = current.data[0]['current_stock'] + quantity_change
            supabase.table('inventory').update({
                'current_stock': max(0, new_stock)  # 負の在庫を防ぐ
            }).eq('common_code', common_code).execute()
            
            logger.info(f"在庫更新: {common_code} → {new_stock}個")
            
    except Exception as e:
        logger.error(f"在庫更新エラー: {str(e)}")

def check_amazon_mapping_coverage():
    """
    Amazon ASINマッピングのカバレッジを確認
    """
    # product_masterでAmazon ASINが設定されている商品を確認
    result = supabase.table('product_master').select('common_code, product_name, amazon_asin').not_.is_('amazon_asin', 'null').execute()
    
    logger.info(f"\n=== Amazon ASINマッピング状況 ===")
    logger.info(f"マッピング済み商品数: {len(result.data)}件")
    
    for item in result.data[:10]:  # 最初の10件を表示
        logger.info(f"  {item['common_code']}: {item['product_name']} → ASIN: {item['amazon_asin']}")
    
    return len(result.data)

if __name__ == "__main__":
    # マッピング状況を確認
    check_amazon_mapping_coverage()