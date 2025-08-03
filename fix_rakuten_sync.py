# -*- coding: utf-8 -*-
"""
楽天同期問題の修正案
unified_platform_api.pyのsync_rakuten_orders関数を実際の楽天API同期に修正
"""

fix_code = """
async def sync_rakuten_orders(date_from: str, date_to: str):
    '''楽天注文同期 - 実際の楽天APIから注文データを取得'''
    try:
        from datetime import datetime, timedelta
        from api.rakuten_api import RakutenAPI
        
        # 日付の設定
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')
        
        start_date = datetime.strptime(date_from, '%Y-%m-%d')
        end_date = datetime.strptime(date_to, '%Y-%m-%d')
        
        # 楽天API初期化
        rakuten_api = RakutenAPI()
        
        # 注文データの取得
        orders = rakuten_api.get_orders(start_date, end_date)
        
        # データベースに保存
        result = rakuten_api.save_to_supabase(orders)
        
        return {
            "status": "success",
            "message": f"楽天注文同期完了: {date_from} から {date_to}",
            "period": f"{date_from} - {date_to}",
            "orders_processed": result.get('total_orders', 0),
            "items_processed": result.get('items_success', 0),
            "success_rate": result.get('success_rate', '0%'),
            "details": result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"楽天同期エラー: {str(e)}",
            "date_from": date_from,
            "date_to": date_to
        }
"""

print("=== 楽天同期修正案 ===")
print("問題: unified_platform_api.py の sync_rakuten_orders 関数が実際の楽天API同期を行っていない")
print("修正: 上記のコードで置き換える必要があります")
print("\n修正対象ファイル:")
print("- rakuten-order-sync/api/unified_platform_api.py (Line 178-180)")
print("\n修正後の効果:")
print("- 実際の楽天APIから注文データを取得")
print("- SKU・選択肢コード情報も含めた完全なデータ保存")
print("- 2/12-3/30の期間のデータが正しく取得される")
print("\n次のステップ:")
print("1. unified_platform_api.py の sync_rakuten_orders 関数を上記コードで置き換え")
print("2. Cloud Run サービスの再デプロイ")
print("3. /api/platform_sync?platform=rakuten&start_date=2025-02-12&end_date=2025-03-30 で再同期")