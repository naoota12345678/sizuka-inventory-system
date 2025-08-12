#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
C01を choice_code_mapping テーブルに追加
product_master から選択肢コードを削除する前準備
"""

from supabase import create_client
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def add_c01_to_choice_code_mapping():
    """C01を choice_code_mapping テーブルに追加"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("=== C01を choice_code_mapping に追加 ===")
    
    # 1. C01が既に登録されているか確認
    existing = supabase.table("choice_code_mapping").select("*").eq("choice_info->>choice_code", "C01").execute()
    
    if existing.data:
        logger.info("C01は既にchoice_code_mappingに登録されています")
        logger.info(f"  共通コード: {existing.data[0].get('common_code')}")
        logger.info(f"  商品名: {existing.data[0].get('product_name')}")
        return False
    
    # 2. product_masterからC01の情報を取得
    product_info = supabase.table("product_master").select("*").eq("common_code", "C01").execute()
    
    if product_info.data:
        product_name = product_info.data[0].get('product_name', 'コーンフレーク')
        logger.info(f"product_masterからC01情報を取得: {product_name}")
    else:
        product_name = "コーンフレーク"
        logger.info("product_masterにC01がありませんでした。デフォルト名を使用します")
    
    # 3. C01をchoice_code_mappingに追加
    new_record = {
        'choice_info': {
            'choice_code': 'C01',
            'choice_name': 'C01 Choice',
            'choice_value': product_name,
            'category': 'manual_addition',
            'added_date': datetime.now(timezone.utc).isoformat()
        },
        'common_code': 'CM204',  # 新しい共通コードを割り当て
        'product_name': product_name,
        'rakuten_sku': 'CHOICE_C01',  # NOT NULL制約対応
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        result = supabase.table("choice_code_mapping").insert(new_record).execute()
        
        if result.data:
            logger.info("SUCCESS: C01を choice_code_mapping に追加成功")
            logger.info(f"  選択肢コード: C01")
            logger.info(f"  共通コード: CM204")
            logger.info(f"  商品名: {product_name}")
            return True
        else:
            logger.error("FAILED: C01の追加に失敗しました")
            return False
            
    except Exception as e:
        logger.error(f"エラー: {str(e)}")
        return False

def verify_all_choice_codes():
    """すべての選択肢コードがchoice_code_mappingに登録されているか確認"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("\n=== 選択肢コード登録状況の最終確認 ===")
    
    choice_codes = ['S01', 'S02', 'C01', 'P01']
    all_registered = True
    
    for code in choice_codes:
        result = supabase.table("choice_code_mapping").select(
            "common_code, product_name"
        ).eq("choice_info->>choice_code", code).execute()
        
        if result.data:
            logger.info(f"OK {code}: 登録済み -> {result.data[0]['common_code']} ({result.data[0]['product_name']})")
        else:
            logger.warning(f"NG {code}: 未登録")
            all_registered = False
    
    return all_registered

if __name__ == "__main__":
    # C01を追加
    success = add_c01_to_choice_code_mapping()
    
    # 全選択肢コードの登録状況を確認
    all_ok = verify_all_choice_codes()
    
    if all_ok:
        print("\nOK: すべての選択肢コードがchoice_code_mappingに登録されています")
        print("次のステップ: 売上ダッシュボードAPIの修正を実行してください")
    else:
        print("\nWARNING: 未登録の選択肢コードがあります。確認してください")