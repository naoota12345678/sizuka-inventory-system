#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
売上ダッシュボードAPIのproduct_master依存を確認・報告
実際の修正はmain_cloudrun.pyで行う必要があるため、影響箇所を特定
"""

from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def analyze_api_dependency():
    """売上ダッシュボードAPIのproduct_master依存を分析"""
    
    logger.info("=== 売上ダッシュボードAPIの依存関係分析 ===")
    
    # main_cloudrun.pyの該当箇所を特定
    api_locations = {
        "/api/inventory_dashboard": {
            "lines": "約275行目",
            "issue": "product_masterから商品名を取得",
            "fix": "choice_code_mappingも参照するようフォールバック処理追加"
        },
        "/api/sales_dashboard": {
            "lines": "約440行目",
            "issue": "product_masterのrakuten_skuから商品名取得",
            "fix": "選択肢コードの場合はchoice_code_mappingを参照"
        },
        "/api/sales_search": {
            "lines": "約3652行目",
            "issue": "product_masterのみを検索",
            "fix": "choice_code_mappingも検索対象に追加"
        }
    }
    
    logger.info("\n修正が必要なAPI:")
    for api, info in api_locations.items():
        logger.info(f"\n{api}:")
        logger.info(f"  場所: {info['lines']}")
        logger.info(f"  問題: {info['issue']}")
        logger.info(f"  修正案: {info['fix']}")
    
    return api_locations

def test_product_name_resolution():
    """商品名取得の現在の動作をテスト"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("\n=== 商品名取得テスト ===")
    
    # テストケース
    test_cases = [
        ("CM001", "product_master"),
        ("CM201", "choice_code_mappingにマッピング済み（P01）"),
        ("S01", "product_masterに存在（削除予定）"),
        ("C01", "product_masterに存在（削除予定）")
    ]
    
    for code, expected_source in test_cases:
        logger.info(f"\n{code}の商品名取得:")
        
        # product_masterから取得
        pm_result = supabase.table("product_master").select(
            "product_name"
        ).eq("common_code", code).execute()
        
        if pm_result.data:
            logger.info(f"  product_master: {pm_result.data[0]['product_name']}")
        else:
            logger.info(f"  product_master: なし")
        
        # choice_code_mappingから取得
        ccm_result = supabase.table("choice_code_mapping").select(
            "product_name"
        ).eq("common_code", code).execute()
        
        if ccm_result.data:
            logger.info(f"  choice_code_mapping: {ccm_result.data[0]['product_name']}")
        else:
            logger.info(f"  choice_code_mapping: なし")
        
        logger.info(f"  期待される取得元: {expected_source}")

def create_fallback_logic():
    """フォールバック処理のサンプルコード生成"""
    
    logger.info("\n=== 推奨フォールバック処理 ===")
    
    sample_code = '''
def get_product_name_safe(common_code, supabase):
    """商品名を安全に取得（product_master削除対応）"""
    
    # 1. product_masterから取得を試みる
    pm_result = supabase.table("product_master").select(
        "product_name"
    ).eq("common_code", common_code).execute()
    
    if pm_result.data and pm_result.data[0].get('product_name'):
        return pm_result.data[0]['product_name']
    
    # 2. choice_code_mappingから取得を試みる（フォールバック）
    ccm_result = supabase.table("choice_code_mapping").select(
        "product_name"
    ).eq("common_code", common_code).execute()
    
    if ccm_result.data and ccm_result.data[0].get('product_name'):
        return ccm_result.data[0]['product_name']
    
    # 3. デフォルト値を返す
    return f"商品_{common_code}"
'''
    
    logger.info("以下のコードをmain_cloudrun.pyに追加することを推奨:")
    print(sample_code)
    
    return sample_code

if __name__ == "__main__":
    # 依存関係を分析
    locations = analyze_api_dependency()
    
    # 現在の動作をテスト
    test_product_name_resolution()
    
    # フォールバック処理のサンプル
    create_fallback_logic()
    
    print("\n" + "="*60)
    print("📋 次のアクション:")
    print("1. main_cloudrun.pyの上記APIエンドポイントを修正")
    print("2. get_product_name_safe関数を追加")
    print("3. 各APIで商品名取得時にこの関数を使用")
    print("="*60)