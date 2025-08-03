#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
選択肢コード対応表の同期
gid=1695475455からR05, R13などの選択肢コードと共通コードのマッピングを取得
"""

import requests
import csv
from io import StringIO
from supabase import create_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

SPREADSHEET_ID = "1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"
CHOICE_CODE_GID = "1695475455"  # 楽天選択肢コード対応表

def sync_choice_codes():
    """選択肢コード対応表をGoogle SheetsからSupabaseに同期"""
    logger.info("=== 選択肢コード対応表の同期 ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Google SheetsからCSVデータを取得
    csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={CHOICE_CODE_GID}"
    
    try:
        logger.info(f"選択肢コード対応表をダウンロード: gid={CHOICE_CODE_GID}")
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        # CSVパース
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        logger.info(f"データ取得成功: {len(data)}行")
        
        if not data:
            logger.error("データが空です")
            return
        
        # 2. データ構造を確認
        logger.info("列名確認:")
        for col in data[0].keys():
            logger.info(f"  - {repr(col)}")
        
        # 最初の3行のサンプルデータを表示
        logger.info("\nサンプルデータ:")
        for i, row in enumerate(data[:3]):
            logger.info(f"行{i+1}: {dict(row)}")
        
        # 3. 選択肢コードと共通コードの列を特定
        choice_code_col = None
        common_code_col = None
        product_name_col = None
        
        # 列名をデコードして検索
        for col in data[0].keys():
            # 日本語が含まれている列名のデバッグ
            try:
                decoded_col = col.encode('latin1').decode('utf-8')
                logger.info(f"列名デコード: {col} -> {decoded_col}")
                
                if '選択肢' in decoded_col and 'コード' in decoded_col:
                    choice_code_col = col
                    logger.info(f"選択肢コード列を検出: {col}")
                elif '共通' in decoded_col and 'コード' in decoded_col:
                    common_code_col = col
                    logger.info(f"共通コード列を検出: {col}")
                elif '商品名' in decoded_col:
                    product_name_col = col
                    logger.info(f"商品名列を検出: {col}")
            except:
                # デコードが失敗した場合は元の列名で判断
                if '選択肢' in col and 'コード' in col:
                    choice_code_col = col
                    logger.info(f"選択肢コード列を検出: {col}")
                elif '共通' in col and 'コード' in col:
                    common_code_col = col
                    logger.info(f"共通コード列を検出: {col}")
                elif '商品名' in col:
                    product_name_col = col
                    logger.info(f"商品名列を検出: {col}")
        
        # 簡易判定も試す
        if not choice_code_col:
            for col in data[0].keys():
                if 'xe9' in col and 'xe3' in col:  # エンコードされた「選択肢コード」を探す
                    choice_code_col = col
                    logger.info(f"選択肢コード列を推定: {col}")
                    break
        
        if not common_code_col:
            for col in data[0].keys():
                if 'xe5' in col and 'xe3' in col:  # エンコードされた「共通コード」を探す
                    common_code_col = col
                    logger.info(f"共通コード列を推定: {col}")
                    break
        
        if not choice_code_col or not common_code_col:
            logger.error("必要な列が見つかりません")
            logger.info("利用可能な列:")
            for col in data[0].keys():
                logger.info(f"  - {col}")
            return
        
        # 4. choice_code_mappingテーブルに同期
        logger.info(f"\n選択肢コードマッピング開始: {len(data)}行を処理")
        
        success_count = 0
        error_count = 0
        
        for i, row in enumerate(data):
            choice_code = row.get(choice_code_col, '').strip()
            common_code = row.get(common_code_col, '').strip()
            product_name = row.get(product_name_col, '').strip() if product_name_col else ''
            
            # 空行をスキップ
            if not choice_code or not common_code:
                continue
            
            # 選択肢コードのパターンチェック（大文字英字1文字+数字2桁）
            # L01, R05, N03などの形式をサポート
            if not (len(choice_code) == 3 and choice_code[0].isupper() and choice_code[1:].isdigit()):
                logger.debug(f"スキップ（選択肢コード形式ではない）: {choice_code}")
                continue
            
            try:
                logger.info(f"行{i+1}: Choice='{choice_code}', Common='{common_code}'")
                
                # 楽天SKUの有無を確認（列名の文字化けにも対応）
                rakuten_sku = ''
                for col_key, col_value in row.items():
                    if 'SKU' in col_key or '管理' in col_key:
                        rakuten_sku = str(col_value).strip()
                        break
                has_single_sale = bool(rakuten_sku)  # 楽天SKUがあれば単品販売もあり
                
                # choice_infoをJSONB形式で準備
                choice_info = {
                    "choice_code": choice_code,
                    "product_name": product_name,
                    "rakuten_sku": rakuten_sku,
                    "has_single_sale": has_single_sale,
                    "sale_type": "単品+選択肢" if has_single_sale else "選択肢のみ"
                }
                
                # 既存レコードをチェック（choice_infoのchoice_codeで検索）
                # JSONB検索の構文を修正
                existing = supabase.table("choice_code_mapping").select("id").eq("choice_info->>choice_code", choice_code).execute()
                
                # rakuten_skuの値を設定（nullの場合は空文字列）
                data_to_save = {
                    "common_code": common_code,
                    "choice_info": choice_info,
                    "product_name": product_name,
                    "rakuten_sku": rakuten_sku if rakuten_sku else ""  # 空文字列でnull制約を回避
                }
                
                if existing.data:
                    # 更新
                    result = supabase.table("choice_code_mapping").update(data_to_save).eq("choice_info->>choice_code", choice_code).execute()
                    logger.info(f"  UPDATED: {choice_code} -> {common_code} ({choice_info['sale_type']})")
                else:
                    # 新規作成
                    result = supabase.table("choice_code_mapping").insert(data_to_save).execute()
                    logger.info(f"  INSERTED: {choice_code} -> {common_code} ({choice_info['sale_type']})")
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"エラー（行{i+1}）: {str(e)}")
                error_count += 1
        
        logger.info(f"\n=== 同期完了 ===")
        logger.info(f"成功: {success_count}件")
        logger.info(f"エラー: {error_count}件")
        
        # 5. 最終確認
        total_count = supabase.table("choice_code_mapping").select("id", count="exact").execute()
        logger.info(f"choice_code_mappingテーブル総件数: {total_count.count}件")
        
    except Exception as e:
        logger.error(f"同期エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== 選択肢コード対応表の同期開始 ===")
    sync_choice_codes()
    print("\n同期完了！")