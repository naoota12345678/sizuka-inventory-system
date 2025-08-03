#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheets CSV直接ダウンロード（改良版）
公開シートから確実にデータを取得してSupabaseに同期
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

SPREADSHEET_ID = "1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"

def get_sheet_data_csv(gid=0):
    """Google SheetsからCSV形式でデータを取得"""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
        
        logger.info(f"Google SheetsからCSVダウンロード: gid={gid}")
        
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        # CSVパース
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        logger.info(f"CSVダウンロード成功: {len(data)}行")
        
        # 列名をログ出力
        if data:
            logger.info(f"利用可能な列: {list(data[0].keys())}")
        
        return data
        
    except Exception as e:
        logger.error(f"CSVダウンロードエラー: {str(e)}")
        return None

def find_mapping_columns(data):
    """楽天SKUと共通コードの列を自動検出"""
    if not data:
        return None, None
    
    columns = list(data[0].keys())
    
    sku_column = None
    common_code_column = None
    
    # 楽天SKU列を探す
    for col in columns:
        if any(keyword in col.lower() for keyword in ['楽天']):  # 楽天列を優先
            sku_column = col
            logger.info(f"楽天SKU列発見: {col}")
            break
    
    # 共通コード列を探す - sizuka+列をチェック
    for col in columns:
        if 'sizuka' in col.lower() or '共通' in col or 'コード' in col:
            common_code_column = col
            logger.info(f"共通コード列発見: {col}")
            break
    
    return sku_column, common_code_column

def sync_product_master_csv():
    """CSVダウンロードでproduct_masterを同期"""
    logger.info("=== Google Sheets CSV同期（改良版） ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # gid=1290908701 の「商品番号マッピング基本表」を使用
    sheet_data = get_sheet_data_csv(1290908701)
    
    if sheet_data and len(sheet_data) > 10:
        # 実際のデータの最初の数行を確認してrakuten_skuを見つける
        logger.info("データサンプル確認:")
        for i, row in enumerate(sheet_data[:3]):
            logger.info(f"行{i+1}: {list(row.keys())}")
            logger.info(f"値サンプル: {dict(list(row.items())[:3])}")
        
        # 商品番号マッピング基本表の列を探す
        sku_column = None
        common_code_column = None
        
        columns = list(sheet_data[0].keys())
        for col in columns:
            # 楽天SKU列を探す
            if any(keyword in col for keyword in ['楽天', 'rakuten', 'SKU']):
                sku_column = col
                logger.info(f"楽天SKU列発見: {col}")
            
            # 共通コード列を探す
            elif any(keyword in col for keyword in ['共通', 'common', 'コード']):
                common_code_column = col
                logger.info(f"共通コード列発見: {col}")
        
        # 列名で見つからない場合は、データ内容で推定
        if not sku_column or not common_code_column:
            logger.info("列名で見つからないため、データ内容で推定します")
            for col in columns:
                sample_values = [row.get(col, '') for row in sheet_data[:10] if row.get(col)]
                if sample_values:
                    # 楽天SKU列の推定：数字で構成されていて長さが4桁以上
                    if not sku_column:
                        numeric_count = sum(1 for val in sample_values if str(val).isdigit() and len(str(val)) >= 4)
                        if numeric_count >= 3:
                            sku_column = col
                            logger.info(f"楽天SKU列を推定: {col}")
                    
                    # 共通コード列の推定：CM### や R## 形式
                    if not common_code_column:
                        code_count = sum(1 for val in sample_values if str(val).startswith(('CM', 'R', 'N', 'P', 'S')))
                        if code_count >= 3:
                            common_code_column = col
                            logger.info(f"共通コード列を推定: {col}")
    
    if not sheet_data:
        logger.error("適切なマッピングデータが見つかりませんでした")
        return False
    
    if not sku_column or not common_code_column:
        logger.error(f"必要な列が見つかりません: SKU={sku_column}, Common={common_code_column}")
        return False
    
    success_count = 0
    error_count = 0
    
    logger.info(f"マッピング開始: {len(sheet_data)}行を処理")
    
    processed_count = 0
    skipped_count = 0
    
    for row in sheet_data:
        try:
            rakuten_sku = row.get(sku_column, '').strip()
            common_code = row.get(common_code_column, '').strip()
            
            # 商品名を探す
            product_name = ''
            for key, value in row.items():
                if any(keyword in key for keyword in ['商品名', 'name', '名前']):
                    if value and value.strip():
                        product_name = value.strip()
                        break
            
            # デバッグ：最初の数行をログ出力
            if processed_count < 5:
                logger.info(f"行{processed_count+1}: SKU='{rakuten_sku}', Common='{common_code}'")
            
            # 有効なデータのみ処理
            if not rakuten_sku or not common_code:
                skipped_count += 1
                continue
            
            # より緩い楽天SKUのパターンチェック
            if not (rakuten_sku.isdigit() and len(rakuten_sku) >= 4):
                skipped_count += 1
                continue
            
            processed_count += 1
            
            # データ準備
            mapping_data = {
                "common_code": common_code,
                "rakuten_sku": rakuten_sku,
                "product_name": product_name or f"商品_{common_code}",
                "product_type": "単品",
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 既存データチェック
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
    
    logger.info(f"CSV同期完了: {success_count} success, {error_count} errors")
    logger.info(f"処理統計: {processed_count} 処理, {skipped_count} スキップ")
    
    # 最終確認
    total_mappings = supabase.table("product_master").select("*").not_.is_("rakuten_sku", "null").execute()
    logger.info(f"総楽天SKUマッピング: {len(total_mappings.data)}件")
    
    return success_count > 0

def test_full_sync():
    """完全同期テスト"""
    logger.info("=== 完全同期テスト ===")
    
    # 現在のマッピング数
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    before = supabase.table("product_master").select("*").not_.is_("rakuten_sku", "null").execute()
    before_count = len(before.data)
    
    logger.info(f"同期前のマッピング: {before_count}件")
    
    # 同期実行
    result = sync_product_master_csv()
    
    # 同期後のマッピング数
    after = supabase.table("product_master").select("*").not_.is_("rakuten_sku", "null").execute()
    after_count = len(after.data)
    
    logger.info(f"同期後のマッピング: {after_count}件")
    logger.info(f"増加分: {after_count - before_count}件")
    
    if result and after_count > before_count:
        logger.info("同期成功 - マッピングが増加しました")
        logger.info("これで楽天注文のマッピング成功率が大幅に向上します")
        return True
    else:
        logger.error("同期に問題があります")
        return False

if __name__ == "__main__":
    print("=== Google Sheets CSV改良版同期 ===")
    
    result = test_full_sync()
    
    if result:
        print("\n成功: Google SheetsからSupabaseへの同期完了")
        print("マッピング率が大幅に向上することが期待されます")
    else:
        print("\n同期に問題がありました")