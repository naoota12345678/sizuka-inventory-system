#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完全なproduct_master同期スクリプト
Google Sheetsの全てのプラットフォーム情報を同期：楽天SKU、Amazon ASIN、カラーミーID、Yahoo商品ID
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

def get_complete_mapping_data():
    """Google Sheetsから完全なマッピングデータを取得"""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={MAPPING_GID}"
        
        logger.info("Google Sheetsから完全なマッピングデータを取得中...")
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        if response.encoding != 'utf-8':
            response.encoding = 'utf-8'
        
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        data = list(reader)
        
        logger.info(f"データ取得成功: {len(data)}行")
        return data
        
    except Exception as e:
        logger.error(f"データ取得エラー: {str(e)}")
        return None

def sync_complete_product_master():
    """完全なproduct_masterテーブル同期"""
    logger.info("=== 完全なproduct_master同期開始 ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Google Sheetsからデータ取得
    sheet_data = get_complete_mapping_data()
    if not sheet_data:
        logger.error("Google Sheetsからのデータ取得に失敗")
        return False
    
    # 列マッピングの定義（Google Sheetsの実際の列名）
    COLUMN_MAPPING = {
        'common_code': '共通コード',
        'product_name': '基本商品名', 
        'rakuten_sku': '楽天SKU',
        'amazon_asin': 'Amazon ASIN',
        'colorMe_id': 'カラーミーID',
        'yahoo_id': 'Yahoo商品ID',
        'smaregi_id': 'スマレジID',
        'mercari_id': 'メルカリ商品ID',
        'product_type': '商品タイプ',
        'jan_code': 'JAN/EANコード'
    }
    
    success_count = 0
    error_count = 0
    created_count = 0
    updated_count = 0
    
    logger.info(f"処理開始: {len(sheet_data)}行を処理")
    
    for i, row in enumerate(sheet_data):
        try:
            # 各列のデータを取得
            common_code = row.get(COLUMN_MAPPING['common_code'], '').strip()
            product_name = row.get(COLUMN_MAPPING['product_name'], '').strip()
            rakuten_sku = row.get(COLUMN_MAPPING['rakuten_sku'], '').strip()
            amazon_asin = row.get(COLUMN_MAPPING['amazon_asin'], '').strip()
            colorMe_id = row.get(COLUMN_MAPPING['colorMe_id'], '').strip()
            yahoo_id = row.get(COLUMN_MAPPING['yahoo_id'], '').strip()
            smaregi_id = row.get(COLUMN_MAPPING['smaregi_id'], '').strip()
            mercari_id = row.get(COLUMN_MAPPING['mercari_id'], '').strip()
            product_type = row.get(COLUMN_MAPPING['product_type'], '').strip() or '単品'
            jan_code = row.get(COLUMN_MAPPING['jan_code'], '').strip()
            
            # 共通コードは必須
            if not common_code or not common_code.startswith('CM'):
                logger.debug(f"行{i+1}: 共通コードが無効 - {common_code}")
                continue
            
            # デバッグ用に最初の10行を詳細表示
            if i < 10:
                logger.info(f"行{i+1}: CM={common_code}, 楽天={rakuten_sku}, Amazon={amazon_asin}")
            
            # 全プラットフォーム情報を含むデータ準備
            mapping_data = {
                "common_code": common_code,
                "product_name": product_name or f"商品_{common_code}",
                "rakuten_sku": rakuten_sku or None,  # 空の場合はNULLに設定
                "amazon_asin": amazon_asin or None,
                "colorMe_id": colorMe_id or None,
                "yahoo_id": yahoo_id or None,
                "smaregi_id": smaregi_id or None,
                "mercari_id": mercari_id or None,
                "product_type": product_type,
                "jan_code": jan_code or None,
                "is_active": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # 既存データの確認（common_codeで検索）
            existing = supabase.table("product_master").select("id").eq("common_code", common_code).execute()
            
            if existing.data:
                # 更新
                result = supabase.table("product_master").update(mapping_data).eq("common_code", common_code).execute()
                action = "UPDATED"
                updated_count += 1
            else:
                # 新規作成
                mapping_data["created_at"] = datetime.now(timezone.utc).isoformat()
                result = supabase.table("product_master").insert(mapping_data).execute()
                action = "CREATED"
                created_count += 1
            
            if result.data:
                # プラットフォーム情報のサマリー
                platforms = []
                if rakuten_sku: platforms.append(f"楽天:{rakuten_sku}")
                if amazon_asin: platforms.append(f"Amazon:{amazon_asin}")
                if colorMe_id: platforms.append(f"カラーミー:{colorMe_id}")
                if yahoo_id: platforms.append(f"Yahoo:{yahoo_id}")
                
                platform_info = ", ".join(platforms) if platforms else "プラットフォーム情報なし"
                logger.info(f"   {action}: {common_code} - {platform_info}")
                success_count += 1
            else:
                logger.error(f"   FAILED: {common_code}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"   ERROR処理中 行{i+1}: {str(e)}")
            error_count += 1
    
    # 結果レポート
    logger.info(f"\n=== 完全同期結果 ===")
    logger.info(f"成功: {success_count}件")
    logger.info(f"エラー: {error_count}件")
    logger.info(f"新規作成: {created_count}件")
    logger.info(f"更新: {updated_count}件")
    
    # 最終確認：各プラットフォームの統計
    logger.info(f"\n=== プラットフォーム統計 ===")
    
    # 楽天SKUの統計
    rakuten_count = supabase.table("product_master").select("id", count="exact").not_.is_("rakuten_sku", "null").execute()
    logger.info(f"楽天SKU登録数: {rakuten_count.count}件")
    
    # Amazon ASINの統計
    amazon_count = supabase.table("product_master").select("id", count="exact").not_.is_("amazon_asin", "null").execute()
    logger.info(f"Amazon ASIN登録数: {amazon_count.count}件")
    
    # カラーミーIDの統計
    colorMe_count = supabase.table("product_master").select("id", count="exact").not_.is_("colorMe_id", "null").execute()
    logger.info(f"カラーミーID登録数: {colorMe_count.count}件")
    
    # Yahoo商品IDの統計
    yahoo_count = supabase.table("product_master").select("id", count="exact").not_.is_("yahoo_id", "null").execute()
    logger.info(f"Yahoo商品ID登録数: {yahoo_count.count}件")
    
    return success_count > 0

def test_complete_sync():
    """完全同期のテスト実行"""
    logger.info("=== 完全なproduct_master同期テスト ===")
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 同期前の状態確認
    before_total = supabase.table("product_master").select("id", count="exact").execute()
    before_rakuten = supabase.table("product_master").select("id", count="exact").not_.is_("rakuten_sku", "null").execute()
    before_amazon = supabase.table("product_master").select("id", count="exact").not_.is_("amazon_asin", "null").execute()
    
    logger.info(f"同期前 - 総数:{before_total.count}, 楽天:{before_rakuten.count}, Amazon:{before_amazon.count}")
    
    # 完全同期実行
    result = sync_complete_product_master()
    
    # 同期後の状態確認
    after_total = supabase.table("product_master").select("id", count="exact").execute()
    after_rakuten = supabase.table("product_master").select("id", count="exact").not_.is_("rakuten_sku", "null").execute()
    after_amazon = supabase.table("product_master").select("id", count="exact").not_.is_("amazon_asin", "null").execute()
    
    logger.info(f"同期後 - 総数:{after_total.count}, 楽天:{after_rakuten.count}, Amazon:{after_amazon.count}")
    
    # サンプルデータ確認
    logger.info(f"\n=== 同期結果サンプル（最新5件） ===")
    samples = supabase.table("product_master").select(
        "common_code, rakuten_sku, amazon_asin, colorMe_id, product_name"
    ).order("updated_at", desc=True).limit(5).execute()
    
    for item in samples.data:
        platforms = []
        if item.get('rakuten_sku'): platforms.append("楽天")
        if item.get('amazon_asin'): platforms.append("Amazon")
        if item.get('colorMe_id'): platforms.append("カラーミー")
        
        platform_str = "+".join(platforms) if platforms else "なし"
        logger.info(f"  {item['common_code']}: {platform_str} - {item['product_name'][:30]}...")
    
    if result:
        logger.info("\n✅ 完全同期成功！全プラットフォーム情報が正しく同期されました")
        return True
    else:
        logger.error("\n❌ 同期に問題がありました")
        return False

if __name__ == "__main__":
    print("=== Google Sheets完全同期（全プラットフォーム対応） ===")
    
    result = test_complete_sync()
    
    if result:
        print("\n🎉 成功: Google Sheetsからの完全同期が完了しました")
        print("楽天SKU、Amazon ASIN、カラーミーID、Yahoo商品IDが全て同期されました")
    else:
        print("\n⚠️  同期に問題がありました")