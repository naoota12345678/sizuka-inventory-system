#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
楽天APIレスポンス構造の詳細分析
実際のSKU情報がどのフィールドに格納されているかを調査
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from supabase import create_client
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def analyze_rakuten_api_response():
    """楽天APIレスポンスの詳細分析"""
    logger.info("=== 楽天APIレスポンス構造分析 ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. order_itemsテーブルから最新のデータを取得（extended_rakuten_dataを含む）
    try:
        # extended_rakuten_dataがnullでないレコードを取得
        response = supabase.table("order_items").select("*").not_.is_("extended_rakuten_data", "null").limit(10).execute()
        
        if not response.data:
            logger.error("extended_rakuten_dataを持つレコードが見つかりません")
            
            # 通常のレコードも確認
            normal_response = supabase.table("order_items").select("*").limit(10).execute()
            if normal_response.data:
                logger.info(f"通常レコード数: {len(normal_response.data)}")
                for i, item in enumerate(normal_response.data[:3]):
                    logger.info(f"\n=== レコード {i+1} ===")
                    logger.info(f"product_code: {item.get('product_code')}")
                    logger.info(f"rakuten_variant_id: {item.get('rakuten_variant_id')}")
                    logger.info(f"rakuten_item_number: {item.get('rakuten_item_number')}")
                    logger.info(f"rakuten_sku: {item.get('rakuten_sku')}")
                    logger.info(f"choice_code: {item.get('choice_code')}")
            return
        
        logger.info(f"分析対象レコード数: {len(response.data)}")
        
        # 2. 各レコードのextended_rakuten_dataを分析
        sku_fields_found = {}
        sample_data = []
        
        for i, item in enumerate(response.data):
            logger.info(f"\n=== レコード {i+1} 分析 ===")
            
            # 基本フィールド
            logger.info(f"product_code: {item.get('product_code')}")
            logger.info(f"product_name: {item.get('product_name')}")
            logger.info(f"rakuten_variant_id: {item.get('rakuten_variant_id')}")
            logger.info(f"rakuten_item_number: {item.get('rakuten_item_number')}")
            logger.info(f"rakuten_sku: {item.get('rakuten_sku')}")
            logger.info(f"sku_type: {item.get('sku_type')}")
            
            # extended_rakuten_dataの詳細分析
            extended_data = item.get('extended_rakuten_data')
            if extended_data:
                logger.info("\nextended_rakuten_data内容:")
                
                # raw_sku_dataを確認
                raw_sku = extended_data.get('raw_sku_data', {})
                if raw_sku:
                    logger.info(f"  extraction_method: {raw_sku.get('extraction_method')}")
                    logger.info(f"  extracted_sku: {raw_sku.get('extracted_sku')}")
                    
                    # original_sku_infoの構造を詳細に分析
                    original_sku_info = raw_sku.get('original_sku_info', [])
                    if original_sku_info:
                        logger.info(f"  original_sku_info: {len(original_sku_info)}個のSKU情報")
                        for j, sku_info in enumerate(original_sku_info[:2]):  # 最初の2個だけ表示
                            logger.info(f"    SKU {j+1}: {json.dumps(sku_info, ensure_ascii=False, indent=2)}")
                
                # サンプルデータとして保存
                if i < 3:
                    sample_data.append({
                        'product_code': item.get('product_code'),
                        'product_name': item.get('product_name'),
                        'rakuten_sku': item.get('rakuten_sku'),
                        'extended_data': extended_data
                    })
        
        # 3. 楽天APIの実際の呼び出しをシミュレート
        logger.info("\n=== 楽天API呼び出しシミュレーション ===")
        
        # rakuten-order-sync内のrakuten_api.pyをインポート
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), 'rakuten-order-sync'))
        
        try:
            from api.rakuten_api import RakutenAPI
            
            # RakutenAPIインスタンスを作成
            api = RakutenAPI()
            
            # 最新の注文データを少量取得してみる
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(hours=1)  # 1時間前から
            
            logger.info(f"期間: {start_date} から {end_date}")
            
            # APIを呼び出し（実際のレスポンスを確認）
            orders = api.get_orders(start_date, end_date)
            
            if orders:
                logger.info(f"\n取得した注文数: {len(orders)}")
                
                # 最初の注文の詳細を分析
                for order_idx, order in enumerate(orders[:1]):  # 最初の1件のみ
                    logger.info(f"\n=== 注文 {order_idx + 1} の詳細 ===")
                    
                    # PackageModelListを確認
                    packages = order.get("PackageModelList", [])
                    logger.info(f"パッケージ数: {len(packages)}")
                    
                    for pkg_idx, package in enumerate(packages[:1]):  # 最初のパッケージのみ
                        items = package.get("ItemModelList", [])
                        logger.info(f"  パッケージ {pkg_idx + 1} の商品数: {len(items)}")
                        
                        for item_idx, item in enumerate(items[:2]):  # 最初の2商品のみ
                            logger.info(f"\n  === 商品 {item_idx + 1} ===")
                            
                            # 重要なフィールドを全て確認
                            important_fields = [
                                "itemId", "itemNumber", "itemName", 
                                "skuId", "variantId", "janCode",
                                "SkuModelList", "selectedChoice",
                                "shopItemCode", "merchantDefinedSkuId"
                            ]
                            
                            for field in important_fields:
                                value = item.get(field)
                                if value:
                                    logger.info(f"    {field}: {value}")
                            
                            # SkuModelListの詳細
                            sku_models = item.get("SkuModelList", [])
                            if sku_models:
                                logger.info(f"    SkuModelList詳細: {len(sku_models)}個")
                                for sku_idx, sku in enumerate(sku_models[:2]):
                                    logger.info(f"      SKU {sku_idx + 1}:")
                                    logger.info(f"        {json.dumps(sku, ensure_ascii=False, indent=8)}")
            else:
                logger.info("最近の注文データがありません")
                
        except Exception as e:
            logger.error(f"楽天API呼び出しエラー: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 4. 分析結果のサマリー
        logger.info("\n=== 分析結果サマリー ===")
        logger.info("1. 現在のデータベース状況:")
        logger.info("   - rakuten_variant_id: ほぼ全てnull")
        logger.info("   - rakuten_item_number: ほぼ全てnull")
        logger.info("   - rakuten_sku: 一部のレコードで値あり")
        
        logger.info("\n2. 推測される問題:")
        logger.info("   - APIレスポンスのフィールド名が想定と異なる")
        logger.info("   - SKU情報の抽出ロジックが不完全")
        logger.info("   - itemNumberとitemIdの混同")
        
        logger.info("\n3. 次のアクション:")
        logger.info("   - 実際のAPIレスポンスから正しいフィールドマッピングを確認")
        logger.info("   - _prepare_item_data関数の修正")
        logger.info("   - SKU抽出ロジックの改善")
        
        # サンプルデータをファイルに保存
        if sample_data:
            with open("rakuten_api_sample_data.json", "w", encoding="utf-8") as f:
                json.dump(sample_data, f, ensure_ascii=False, indent=2)
            logger.info(f"\nサンプルデータを rakuten_api_sample_data.json に保存しました")
            
    except Exception as e:
        logger.error(f"分析エラー: {str(e)}")
        import traceback
        traceback.print_exc()

def check_actual_sku_values():
    """実際のSKU値の分布を確認"""
    logger.info("\n=== SKU値の分布確認 ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # product_codeの分布を確認
    response = supabase.table("order_items").select("product_code").limit(50).execute()
    
    if response.data:
        product_codes = {}
        for item in response.data:
            code = item.get('product_code', 'NULL')
            if code not in product_codes:
                product_codes[code] = 0
            product_codes[code] += 1
        
        logger.info("\nproduct_codeの分布:")
        for code, count in sorted(product_codes.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {code}: {count}件")
        
        # product_codeのパターンを分析
        patterns = {
            '10000XXX形式': 0,
            '1XXX形式': 0,
            'TEST形式': 0,
            'その他': 0
        }
        
        for code in product_codes.keys():
            if code.startswith('10000'):
                patterns['10000XXX形式'] += product_codes[code]
            elif code.startswith('1') and code.isdigit() and len(code) == 4:
                patterns['1XXX形式'] += product_codes[code]
            elif 'TEST' in code:
                patterns['TEST形式'] += product_codes[code]
            else:
                patterns['その他'] += product_codes[code]
        
        logger.info("\nproduct_codeのパターン:")
        for pattern, count in patterns.items():
            logger.info(f"  {pattern}: {count}件")

if __name__ == "__main__":
    print("=== 楽天APIレスポンス構造の詳細分析 ===")
    
    # 1. 既存データの分析
    analyze_rakuten_api_response()
    
    # 2. SKU値の分布確認
    check_actual_sku_values()
    
    print("\n分析完了！")