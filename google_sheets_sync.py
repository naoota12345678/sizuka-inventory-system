#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheetsとの同期機能
1日1回実行してマッピングデータを更新
"""

import requests
import csv
from io import StringIO
from supabase import create_client
from datetime import datetime, timezone
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

# Google Sheets CSV export URLs
GOOGLE_SHEETS_URLS = {
    "choice_mapping": "https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/export?format=csv&gid=1290908701",  # 選択肢コード対応表
    "bundle_components": "https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/export?format=csv&gid=0",  # まとめ商品内訳テーブル
    "product_mapping": "https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/export?format=csv&gid=0"  # 商品番号マッピング基本表 (最初のタブを再確認)
}

def fetch_google_sheet_data(sheet_name):
    """Google Sheetsからデータを取得"""
    try:
        url = GOOGLE_SHEETS_URLS.get(sheet_name)
        if not url:
            logger.error(f"Unknown sheet name: {sheet_name}")
            return None
            
        logger.info(f"Fetching data from Google Sheets: {sheet_name}")
        
        # Google Sheetsのgzip圧縮されたUTF-8レスポンスを正しく処理
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # requestsが自動的にgzipを展開し、UTF-8として解釈
        # 但し、場合によっては文字エンコーディングが不正確な場合がある
        if response.encoding != 'utf-8':
            response.encoding = 'utf-8'
        
        content = response.text
        logger.info(f"Content decoded with encoding: {response.encoding}")
        
        # CSVデータを解析
        csv_data = StringIO(content)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        logger.info(f"Successfully fetched {len(data)} rows from {sheet_name}")
        return data
        
    except Exception as e:
        logger.error(f"Error fetching Google Sheets data for {sheet_name}: {str(e)}")
        return None

def sync_choice_code_mapping():
    """選択肢コード対応表の同期"""
    logger.info("=== Syncing Choice Code Mapping ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Google Sheetsからデータ取得
    sheet_data = fetch_google_sheet_data("choice_mapping")
    if not sheet_data:
        logger.error("Failed to fetch choice mapping data")
        return False
    
    # 列名の動的マッピング（文字化け対応）
    if not sheet_data:
        return False
        
    headers = list(sheet_data[0].keys())
    logger.info(f"Available headers: {headers[:5]}")
    
    # 位置ベースの列マッピング（Google Sheetsの列順序に基づく）
    # 順序: 連番, 共通コード, JAN/EAN, 基本商品名, 楽天SKU, ...
    common_code_col = headers[1] if len(headers) > 1 else None
    product_name_col = headers[3] if len(headers) > 3 else None
    
    if not common_code_col or not product_name_col:
        logger.error("Required columns not found in the expected positions")
        return False
    
    logger.info(f"Using columns: common_code='{common_code_col}', product_name='{product_name_col}'")
    
    success_count = 0
    error_count = 0
    
    for row in sheet_data:
        try:
            # 位置ベースで列データを取得
            common_code = row.get(common_code_col, '').strip()
            product_name = row.get(product_name_col, '').strip()
            
            if not common_code or not common_code.startswith('CM'):
                continue
            
            # choice_info (JSONB) フィールドの準備  
            # 実際の選択肢コードは楽天注文データから抽出されるため、ここではcommon_codeをplaceholderとして使用
            choice_info = {
                "choice_code": common_code,  # placeholderとして使用
                "description": product_name,
                "category": "google_sheets_sync",
                "sync_date": datetime.now(timezone.utc).isoformat()
            }
            
            # データの準備
            mapping_data = {
                "choice_info": choice_info,
                "common_code": common_code,
                "product_name": product_name,
                "rakuten_sku": f"SHEETS_{common_code}",  # 識別用プレフィックス
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 既存データの確認（common_codeで検索）
            existing = supabase.table("choice_code_mapping").select("id").eq("common_code", common_code).execute()
            
            if existing.data:
                # 更新
                result = supabase.table("choice_code_mapping").update(mapping_data).eq("common_code", common_code).execute()
                action = "UPDATED"
            else:
                # 新規挿入
                result = supabase.table("choice_code_mapping").insert(mapping_data).execute()
                action = "CREATED"
            
            if result.data:
                logger.info(f"   {action}: {common_code} ({product_name[:30]}...)")
                success_count += 1
            else:
                logger.error(f"   FAILED: {common_code}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"   ERROR processing {row}: {str(e)}")
            error_count += 1
    
    logger.info(f"Choice code mapping sync completed: {success_count} success, {error_count} errors")
    return error_count == 0

def sync_bundle_components():
    """まとめ商品構成の同期"""
    logger.info("=== Syncing Bundle Components ===")
    
    # 今後実装予定
    logger.info("Bundle components sync - To be implemented")
    return True

def sync_product_mapping():
    """商品番号マッピング基本表の同期（楽天SKU → 共通コード）"""
    logger.info("=== Syncing Product Mapping (Rakuten SKU) ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Google Sheetsからデータ取得
    sheet_data = fetch_google_sheet_data("product_mapping")
    if not sheet_data:
        logger.error("Failed to fetch product mapping data")
        return False
    
    success_count = 0
    error_count = 0
    
    for row in sheet_data:
        try:
            # より柔軟な列名検索
            common_code = None
            rakuten_sku = None
            product_name = None
            product_type = '単品'
            
            # 共通コード列を探す
            for key, value in row.items():
                if any(keyword in key for keyword in ['共通', 'コード', 'common', 'Common']):
                    if value and value.strip():
                        common_code = value.strip()
                        break
            
            # 楽天SKU列を探す
            for key, value in row.items():
                if any(keyword in key for keyword in ['楽天', 'SKU', 'sku']):
                    if value and value.strip():
                        rakuten_sku = value.strip()
                        break
            
            # 商品名列を探す
            for key, value in row.items():
                if any(keyword in key for keyword in ['商品名', '基準', 'product', 'name']):
                    if value and value.strip():
                        product_name = value.strip()
                        break
            
            # 商品タイプ列を探す
            for key, value in row.items():
                if any(keyword in key for keyword in ['タイプ', 'type']):
                    if value and value.strip():
                        product_type = value.strip()
                        break
            
            if not common_code or not rakuten_sku:
                logger.debug(f"Skipping row - common_code: {common_code}, rakuten_sku: {rakuten_sku}")
                continue
            
            # データの準備
            mapping_data = {
                "common_code": common_code,
                "rakuten_sku": rakuten_sku,
                "product_name": product_name,
                "product_type": product_type,
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 既存データの確認（common_codeで検索）
            existing = supabase.table("product_master").select("id").eq("common_code", common_code).execute()
            
            if existing.data:
                # 更新
                result = supabase.table("product_master").update(mapping_data).eq("common_code", common_code).execute()
                action = "UPDATED"
            else:
                # 新規挿入
                mapping_data["created_at"] = datetime.now(timezone.utc).isoformat()
                result = supabase.table("product_master").insert(mapping_data).execute()
                action = "CREATED"
            
            if result.data:
                logger.info(f"   {action}: {rakuten_sku} -> {common_code} ({product_name[:30]}...)")
                success_count += 1
            else:
                logger.error(f"   FAILED: {rakuten_sku} -> {common_code}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"   ERROR processing {row}: {str(e)}")
            error_count += 1
    
    logger.info(f"Product mapping sync completed: {success_count} success, {error_count} errors")
    return error_count == 0

def daily_sync():
    """1日1回の同期処理"""
    logger.info(f"=== Daily Google Sheets Sync Started at {datetime.now()} ===")
    
    results = {}
    
    # 各シートの同期
    results['choice_mapping'] = sync_choice_code_mapping()
    results['bundle_components'] = sync_bundle_components()
    results['product_mapping'] = sync_product_mapping()
    
    # 結果サマリー
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    logger.info(f"=== Daily Sync Completed: {success_count}/{total_count} successful ===")
    
    if all(results.values()):
        logger.info("✓ All syncs completed successfully")
        return True
    else:
        logger.error("✗ Some syncs failed")
        for sheet_name, success in results.items():
            status = "✓" if success else "✗"
            logger.info(f"  {status} {sheet_name}")
        return False

if __name__ == "__main__":
    try:
        success = daily_sync()
        
        if success:
            print("Daily sync completed successfully")
        else:
            print("Daily sync completed with errors")
            
    except Exception as e:
        logger.error(f"Daily sync failed: {str(e)}")
        import traceback
        traceback.print_exc()