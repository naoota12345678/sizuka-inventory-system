#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
product_masterから選択肢コード（S01, S02, C01, P01）を削除
事前準備完了後に実行
"""

from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def pre_deletion_check():
    """削除前の最終確認"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("=== 削除前の最終確認 ===")
    
    choice_codes = ['S01', 'S02', 'C01', 'P01']
    all_safe = True
    
    for code in choice_codes:
        logger.info(f"\n{code}の確認:")
        
        # 1. choice_code_mappingに登録されているか
        ccm_result = supabase.table("choice_code_mapping").select(
            "common_code, product_name"
        ).eq("choice_info->>choice_code", code).execute()
        
        if ccm_result.data:
            logger.info(f"  ✅ choice_code_mapping: 登録済み -> {ccm_result.data[0]['common_code']}")
        else:
            logger.warning(f"  ❌ choice_code_mapping: 未登録")
            all_safe = False
        
        # 2. 在庫テーブルで使用されていないか
        inv_result = supabase.table("inventory").select(
            "common_code, current_stock"
        ).eq("common_code", code).execute()
        
        if inv_result.data:
            logger.warning(f"  ⚠️ inventory: 使用中 ({inv_result.data[0]['current_stock']}個)")
            all_safe = False
        else:
            logger.info(f"  ✅ inventory: 未使用")
        
        # 3. product_masterの状態
        pm_result = supabase.table("product_master").select(
            "common_code, product_name, created_at"
        ).eq("common_code", code).execute()
        
        if pm_result.data:
            logger.info(f"  📍 product_master: 存在 (作成日: {pm_result.data[0]['created_at'][:10]})")
        else:
            logger.info(f"  ✅ product_master: 既に削除済み")
    
    return all_safe

def delete_choice_codes():
    """選択肢コードを削除"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("\n=== 選択肢コード削除実行 ===")
    
    choice_codes = ['S01', 'S02', 'C01', 'P01']
    deleted_count = 0
    failed_count = 0
    
    for code in choice_codes:
        try:
            # 削除実行
            result = supabase.table("product_master").delete().eq("common_code", code).execute()
            
            if result.data:
                logger.info(f"✅ {code}: 削除成功")
                deleted_count += 1
            else:
                logger.info(f"ℹ️ {code}: 既に存在しない")
                
        except Exception as e:
            logger.error(f"❌ {code}: 削除失敗 - {str(e)}")
            failed_count += 1
    
    return deleted_count, failed_count

def post_deletion_verify():
    """削除後の検証"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("\n=== 削除後の検証 ===")
    
    # 1. product_masterの統計
    total_result = supabase.table("product_master").select("id", count="exact").execute()
    cm_result = supabase.table("product_master").select("id", count="exact").like("common_code", "CM%").execute()
    
    logger.info(f"product_master総数: {total_result.count}件")
    logger.info(f"CM系商品数: {cm_result.count}件")
    
    # 2. 選択肢コードが残っていないか確認
    choice_codes = ['S01', 'S02', 'C01', 'P01']
    remaining = []
    
    for code in choice_codes:
        check = supabase.table("product_master").select("common_code").eq("common_code", code).execute()
        if check.data:
            remaining.append(code)
    
    if remaining:
        logger.warning(f"⚠️ 削除されなかった選択肢コード: {', '.join(remaining)}")
        return False
    else:
        logger.info("✅ すべての選択肢コードが削除されました")
        return True

if __name__ == "__main__":
    print("="*60)
    print("product_master 選択肢コード削除ツール")
    print("="*60)
    
    # 削除前チェック
    safe_to_delete = pre_deletion_check()
    
    if not safe_to_delete:
        print("\n⚠️ 削除の準備が完了していません")
        print("以下を確認してください:")
        print("1. すべての選択肢コードがchoice_code_mappingに登録されている")
        print("2. 在庫テーブルで選択肢コードが使用されていない")
        print("3. 売上ダッシュボードAPIが修正されている")
        response = input("\nそれでも削除を実行しますか？ (yes/no): ")
        if response.lower() != 'yes':
            print("削除を中止しました")
            exit(0)
    
    # 削除実行
    deleted, failed = delete_choice_codes()
    
    # 削除後検証
    success = post_deletion_verify()
    
    print("\n" + "="*60)
    print("実行結果:")
    print(f"削除成功: {deleted}件")
    print(f"削除失敗: {failed}件")
    
    if success:
        print("\n✅ 選択肢コードの削除が完了しました")
        print("product_masterには商品マスタ（CM系）のみが残っています")
    else:
        print("\n⚠️ 一部の選択肢コードが残っている可能性があります")