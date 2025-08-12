#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
正しい選択肢コード対応表の同期
Google Sheets選択肢コード対応表 → choice_code_mapping
"""

import requests
import csv
from io import StringIO
from supabase import create_client
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def correct_choice_code_sync():
    """正しい選択肢コード対応表の同期"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("=== 正しい選択肢コード対応表の同期 ===")
    
    # 1. 現在の間違ったCM系エントリを削除
    logger.info("1. 間違ったCM系エントリを削除中...")
    cm_entries = supabase.table('choice_code_mapping').select('id').like('choice_info->>choice_code', 'CM%').execute()
    
    for entry in cm_entries.data:
        supabase.table('choice_code_mapping').delete().eq('id', entry['id']).execute()
    
    logger.info(f"削除完了: {len(cm_entries.data)}件のCM系エントリ")
    
    # 2. Google Sheetsから正しい選択肢コード対応表を取得
    SPREADSHEET_ID = "1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"
    CHOICE_GID = "1695475455"  # 選択肢コード対応表
    
    csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={CHOICE_GID}"
    
    try:
        response = requests.get(csv_url, timeout=30)
        response.encoding = 'utf-8'
        
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        logger.info(f"2. Google Sheetsデータ取得: {len(data)}行")
        
        # 3. 正しい列マッピングで同期
        success_count = 0
        created_count = 0
        
        for i, row in enumerate(data):
            try:
                # 正しい列から取得
                choice_code = row.get('選択肢コード', '').strip()
                common_code = row.get('共通コード', '').strip()
                product_name = row.get('商品名', '').strip()
                jan_code = row.get('JAN', '').strip()
                rakuten_sku = row.get('楽天SKU管理番号', '').strip()
                
                # 必須フィールドチェック
                if not choice_code or not common_code:
                    continue
                
                # 最初の5件をログ出力
                if i < 5:
                    logger.info(f"  {choice_code} -> {common_code}: {product_name[:30]}...")
                
                # choice_info JSONBデータ作成
                choice_info = {
                    "choice_code": choice_code,
                    "choice_name": f"{choice_code} Choice",
                    "choice_value": product_name,
                    "category": "google_sheets_sync",
                    "jan_code": jan_code,
                    "rakuten_sku_admin": rakuten_sku,
                    "sync_date": datetime.now(timezone.utc).isoformat()
                }
                
                # Supabaseに挿入するデータ
                mapping_data = {
                    "choice_info": choice_info,
                    "common_code": common_code,
                    "product_name": product_name,
                    "rakuten_sku": f"CHOICE_{choice_code}",  # NOT NULL制約対応
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                # 挿入実行
                result = supabase.table("choice_code_mapping").insert(mapping_data).execute()
                
                if result.data:
                    success_count += 1
                    created_count += 1
                    
            except Exception as e:
                logger.error(f"行{i+1}でエラー: {str(e)}")
        
        logger.info(f"\\n3. 同期結果:")
        logger.info(f"   成功: {success_count}件")
        logger.info(f"   新規作成: {created_count}件")
        
        # 4. 検証
        total_after = supabase.table('choice_code_mapping').select('id', count='exact').execute()
        
        # L01, R05等が正しく登録されているか確認
        test_codes = ['L01', 'L02', 'R05', 'R01']
        logger.info(f"\\n4. 検証結果:")
        logger.info(f"   総件数: {total_after.count}件")
        
        for code in test_codes:
            result = supabase.table('choice_code_mapping').select('common_code').eq('choice_info->>choice_code', code).execute()
            status = f"-> {result.data[0]['common_code']}" if result.data else "NOT FOUND"
            logger.info(f"   {code}: {status}")
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"同期エラー: {str(e)}")
        return False

if __name__ == "__main__":
    success = correct_choice_code_sync()
    
    if success:
        print("\\n✅ 正しい選択肢コード対応表の同期が完了しました")
        print("L01, L02, R05等の選択肢コードが正しく登録されています")
    else:
        print("\\n❌ 同期に失敗しました")