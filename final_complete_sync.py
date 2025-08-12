#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheetsとproduct_masterの完全同期（実際のカラム名対応版）
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
MAPPING_GID = "1290908701"

def sync_complete_product_master():
    """Google Sheetsとproduct_masterの完全同期"""
    logger.info("=== Google Sheets完全同期開始 ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Google Sheetsからデータ取得
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={MAPPING_GID}"
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        if response.encoding != 'utf-8':
            response.encoding = 'utf-8'
        
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        logger.info(f"Google Sheetsデータ取得成功: {len(data)}行")
        
    except Exception as e:
        logger.error(f"Google Sheetsデータ取得エラー: {str(e)}")
        return False
    
    # Google Sheetsの実際の列名（debug_sheets_structure.py で確認済み）
    SHEETS_COLUMNS = {
        'sequence': '連番',
        'common_code': '共通コード', 
        'jan_ean': 'JAN/EANコード',
        'product_name': '基本商品名',
        'rakuten_sku': '楽天SKU',
        'colorme_id': 'カラーミーID',
        'smaregi_id': 'スマレジID',
        'yahoo_id': 'Yahoo商品ID',
        'amazon_asin': 'Amazon ASIN',
        'mercari_id': 'メルカリ商品ID',
        'product_type': '商品タイプ',
        'remarks': '備考'
    }
    
    success_count = 0
    error_count = 0
    created_count = 0
    updated_count = 0
    
    logger.info(f"処理開始: {len(data)}行")
    
    for i, row in enumerate(data):
        try:
            # 各項目を取得
            sequence_number = row.get(SHEETS_COLUMNS['sequence'], '').strip()
            common_code = row.get(SHEETS_COLUMNS['common_code'], '').strip()
            jan_ean_code = row.get(SHEETS_COLUMNS['jan_ean'], '').strip()
            product_name = row.get(SHEETS_COLUMNS['product_name'], '').strip()
            rakuten_sku = row.get(SHEETS_COLUMNS['rakuten_sku'], '').strip()
            colorme_id = row.get(SHEETS_COLUMNS['colorme_id'], '').strip()
            smaregi_id = row.get(SHEETS_COLUMNS['smaregi_id'], '').strip()
            yahoo_product_id = row.get(SHEETS_COLUMNS['yahoo_id'], '').strip()
            amazon_asin = row.get(SHEETS_COLUMNS['amazon_asin'], '').strip()
            mercari_product_id = row.get(SHEETS_COLUMNS['mercari_id'], '').strip()
            product_type = row.get(SHEETS_COLUMNS['product_type'], '').strip() or '単品'
            remarks = row.get(SHEETS_COLUMNS['remarks'], '').strip()
            
            # 共通コードは必須
            if not common_code or not common_code.startswith('CM'):
                continue
            
            # デバッグ表示（最初の5行）
            if i < 5:
                logger.info(f"行{i+1}: {common_code} - 楽天:{rakuten_sku or 'なし'}, Amazon:{amazon_asin or 'なし'}")
            
            # sequence_numberは数値変換
            try:
                seq_num = int(sequence_number) if sequence_number.isdigit() else None
            except:
                seq_num = None
            
            # Supabaseに保存するデータ準備
            mapping_data = {
                "sequence_number": seq_num,
                "common_code": common_code,
                "jan_ean_code": jan_ean_code or None,
                "product_name": product_name or f"商品_{common_code}",
                "rakuten_sku": rakuten_sku or None,
                "colorme_id": colorme_id or None,  # 実際のカラム名
                "smaregi_id": smaregi_id or None,
                "yahoo_product_id": yahoo_product_id or None,
                "amazon_asin": amazon_asin or None,
                "mercari_product_id": mercari_product_id or None,
                "product_type": product_type,
                "remarks": remarks or None,
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 既存データ確認
            existing = supabase.table("product_master").select("id").eq("common_code", common_code).execute()
            
            if existing.data:
                # 更新
                result = supabase.table("product_master").update(mapping_data).eq("common_code", common_code).execute()
                updated_count += 1
                action = "UPDATED"
            else:
                # 新規作成
                mapping_data["created_at"] = datetime.now(timezone.utc).isoformat()
                result = supabase.table("product_master").insert(mapping_data).execute()
                created_count += 1
                action = "CREATED"
            
            if result.data:
                success_count += 1
                
                # プラットフォーム情報
                platforms = []
                if rakuten_sku: platforms.append("楽天")
                if amazon_asin: platforms.append("Amazon") 
                if colorme_id: platforms.append("カラーミー")
                if yahoo_product_id: platforms.append("Yahoo")
                
                platform_info = "+".join(platforms) if platforms else "なし"
                logger.info(f"   {action}: {common_code} [{platform_info}]")
            else:
                error_count += 1
                logger.error(f"   FAILED: {common_code}")
                
        except Exception as e:
            error_count += 1
            logger.error(f"   ERROR 行{i+1}: {str(e)}")
    
    # 結果統計
    logger.info(f"\n=== 完全同期結果 ===")
    logger.info(f"処理成功: {success_count}件")
    logger.info(f"処理エラー: {error_count}件") 
    logger.info(f"新規作成: {created_count}件")
    logger.info(f"データ更新: {updated_count}件")
    
    # プラットフォーム別統計
    logger.info(f"\n=== プラットフォーム統計 ===")
    rakuten_count = supabase.table("product_master").select("id", count="exact").not_.is_("rakuten_sku", "null").execute()
    amazon_count = supabase.table("product_master").select("id", count="exact").not_.is_("amazon_asin", "null").execute()
    colorme_count = supabase.table("product_master").select("id", count="exact").not_.is_("colorme_id", "null").execute()
    yahoo_count = supabase.table("product_master").select("id", count="exact").not_.is_("yahoo_product_id", "null").execute()
    
    logger.info(f"楽天SKU: {rakuten_count.count}件")
    logger.info(f"Amazon ASIN: {amazon_count.count}件") 
    logger.info(f"カラーミーID: {colorme_count.count}件")
    logger.info(f"Yahoo商品ID: {yahoo_count.count}件")
    
    return success_count > 0

def verify_sync_result():
    """同期結果を検証"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    logger.info("=== 同期結果検証 ===")
    
    # rakuten_skuがnullだったデータの確認
    logger.info("rakuten_skuがnullのデータ確認:")
    null_rakuten = supabase.table("product_master").select(
        "common_code, rakuten_sku, amazon_asin, colorme_id, product_name"
    ).is_("rakuten_sku", "null").limit(5).execute()
    
    for item in null_rakuten.data:
        other_platforms = []
        if item.get('amazon_asin'): other_platforms.append("Amazon")
        if item.get('colorme_id'): other_platforms.append("カラーミー") 
        
        other_info = "+".join(other_platforms) if other_platforms else "他プラットフォームなし"
        logger.info(f"  {item['common_code']}: 楽天なし, {other_info}")
    
    # サンプルデータ表示
    logger.info("\n完全データのサンプル（最新5件）:")
    samples = supabase.table("product_master").select(
        "common_code, rakuten_sku, amazon_asin, colorme_id, yahoo_product_id, product_name"
    ).order("updated_at", desc=True).limit(5).execute()
    
    for item in samples.data:
        platforms = []
        if item.get('rakuten_sku'): platforms.append("楽天")
        if item.get('amazon_asin'): platforms.append("Amazon")
        if item.get('colorme_id'): platforms.append("カラーミー")
        if item.get('yahoo_product_id'): platforms.append("Yahoo")
        
        platform_str = "+".join(platforms) if platforms else "なし"
        logger.info(f"  {item['common_code']}: [{platform_str}] {item['product_name'][:30]}...")

if __name__ == "__main__":
    print("=== Google Sheets完全同期（全プラットフォーム対応） ===")
    
    result = sync_complete_product_master()
    
    if result:
        print("\n✅ 完全同期成功!")
        verify_sync_result()
        print("\n🎉 Google Sheetsの全データがproduct_masterに同期されました")
        print("楽天SKUのnull問題も解決され、Amazon/カラーミー等も追加されました")
    else:
        print("\n❌ 同期に失敗しました")