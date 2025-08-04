#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheets API v4を使った直接同期
認証なしで公開シートから確実にデータを取得
"""

import logging
from datetime import datetime, timezone
from supabase import create_client
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

# Google Sheets設定
SPREADSHEET_ID = "1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"
API_KEY = "YOUR_API_KEY_HERE"  # 必要に応じて設定

def get_google_sheets_data_direct(range_name="商品番号マッピング基本表!A:Z"):
    """Google Sheets APIで直接データを取得"""
    try:
        logger.info(f"Google Sheets APIでデータ取得開始: {range_name}")
        
        # APIキーを使用（公開シートの場合）
        service = build('sheets', 'v4', developerKey=API_KEY)
        
        # シートからデータを取得
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.error("シートからデータを取得できませんでした")
            return None
            
        logger.info(f"取得成功: {len(values)}行のデータ")
        
        # ヘッダー行と データ行を分離
        headers = values[0] if values else []
        data_rows = values[1:] if len(values) > 1 else []
        
        # 辞書形式に変換
        formatted_data = []
        for row in data_rows:
            # 行の長さをヘッダーに合わせる（空セル対応）
            while len(row) < len(headers):
                row.append('')
            
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ''
            
            formatted_data.append(row_dict)
        
        return formatted_data
        
    except Exception as e:
        logger.error(f"Google Sheets API エラー: {str(e)}")
        return None

def sync_product_mapping_api():
    """Google Sheets APIを使用した商品マッピング同期"""
    logger.info("=== Google Sheets API 商品マッピング同期 ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Google Sheetsからデータ取得
    sheet_data = get_google_sheets_data_direct()
    if not sheet_data:
        logger.error("Google Sheetsからデータを取得できませんでした")
        return False
    
    logger.info(f"Google Sheetsデータ: {len(sheet_data)}件")
    
    # デバッグ: 列名を確認
    if sheet_data:
        logger.info(f"利用可能な列: {list(sheet_data[0].keys())}")
    
    success_count = 0
    error_count = 0
    
    for row in sheet_data:
        try:
            # 楽天SKUと共通コードを抽出（実際の列名に合わせて調整）
            rakuten_sku = None
            common_code = None
            product_name = None
            
            # 柔軟な列名検索
            for key, value in row.items():
                if value and value.strip():
                    # 楽天SKU列を探す
                    if any(keyword in key for keyword in ['楽天', 'SKU', 'sku', 'Rakuten']):
                        rakuten_sku = value.strip()
                    
                    # 共通コード列を探す
                    elif any(keyword in key for keyword in ['共通', 'コード', 'common', 'Common']):
                        common_code = value.strip()
                    
                    # 商品名列を探す
                    elif any(keyword in key for keyword in ['商品名', '名前', 'name', 'Name']):
                        product_name = value.strip()
            
            if not rakuten_sku or not common_code:
                continue
            
            # データの準備
            mapping_data = {
                "common_code": common_code,
                "rakuten_sku": rakuten_sku,
                "product_name": product_name or f"商品_{common_code}",
                "product_type": "単品",
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 既存データの確認
            existing = supabase.table("product_master").select("id").eq("rakuten_sku", rakuten_sku).execute()
            
            if existing.data:
                # 更新
                result = supabase.table("product_master").update(mapping_data).eq("rakuten_sku", rakuten_sku).execute()
                action = "UPDATED"
            else:
                # 新規挿入
                mapping_data["created_at"] = datetime.now(timezone.utc).isoformat()
                result = supabase.table("product_master").insert(mapping_data).execute()
                action = "CREATED"
            
            if result.data:
                logger.info(f"   {action}: {rakuten_sku} -> {common_code}")
                success_count += 1
            else:
                logger.error(f"   FAILED: {rakuten_sku} -> {common_code}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"   ERROR processing row: {str(e)}")
            error_count += 1
    
    logger.info(f"Google Sheets API同期完了: {success_count} success, {error_count} errors")
    return error_count == 0

def test_api_access():
    """APIアクセステスト（公開シート用）"""
    logger.info("=== Google Sheets API アクセステスト（公開シート）===")
    
    try:
        # 公開シート用の認証なしアクセス
        import os
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ''  # 認証情報をクリア
        
        # 認証なしでサービスを構築
        service = build('sheets', 'v4', cache_discovery=False)
        
        # 公開シートから直接データを取得
        range_name = "A1:Z10"  # 最初の10行をテスト取得
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        logger.info(f"データ取得成功: {len(values)}行")
        
        if values:
            logger.info(f"最初の行: {values[0]}")
        
        return True
        
    except Exception as e:
        logger.error(f"APIアクセスエラー: {str(e)}")
        logger.info("公開シートでもエラーが発生しました")
        logger.info("URLで直接アクセスを試します...")
        
        # フォールバック: 直接HTTPでCSVダウンロード
        try:
            import requests
            csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
            response = requests.get(csv_url, timeout=30)
            
            if response.status_code == 200:
                logger.info("CSVダウンロード成功 - シートは公開されています")
                lines = response.text.split('\n')[:5]
                for i, line in enumerate(lines):
                    logger.info(f"行{i+1}: {line[:100]}...")
                return True
            else:
                logger.error(f"CSVダウンロード失敗: {response.status_code}")
                return False
                
        except Exception as csv_error:
            logger.error(f"CSVダウンロードエラー: {str(csv_error)}")
            return False

if __name__ == "__main__":
    print("=== Google Sheets API 直接同期テスト ===")
    
    # APIアクセステスト
    if test_api_access():
        print("API接続成功 - 同期を実行中...")
        result = sync_product_mapping_api()
        print(f"同期結果: {'成功' if result else '失敗'}")
    else:
        print("API接続失敗 - 設定を確認してください")