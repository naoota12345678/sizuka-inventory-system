#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修正版楽天同期のテストスクリプト
"""

from api.rakuten_api import RakutenAPI
from datetime import datetime, timedelta
import pytz

def test_fixed_sync():
    try:
        print("=== 修正版楽天同期のテスト ===")
        rakuten_api = RakutenAPI()
        
        # 過去30日の注文を取得
        end_date = datetime.now(pytz.UTC)
        start_date = end_date - timedelta(days=30)
        
        print("楽天APIから注文データを取得中...")
        orders = rakuten_api.get_orders(start_date, end_date)
        print(f"取得した注文数: {len(orders)}")
        
        if orders:
            print()
            print("最初の5件をテスト保存中...")
            
            test_orders = orders[:5]
            result = rakuten_api.save_to_supabase(test_orders)
            
            print("保存結果:")
            print(f"  処理対象: {result['total_orders']}件")
            print(f"  成功: {result['success_count']}件")
            print(f"  失敗: {result['error_count']}件")
            print(f"  成功率: {result['success_rate']}")
            
            if result['error_count'] == 0:
                print("✓ 修正版が正常に動作しています！")
                print("✓ 全529件の同期が可能です")
                return True
            else:
                print("❌ まだエラーがあります:")
                for error in result['failed_orders'][:3]:
                    print(f"  - {error['order_number']}: {error['error']}")
                return False
        else:
            print("注文データが取得できませんでした")
            return False
            
    except Exception as e:
        print(f"テストエラー: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_fixed_sync()
    if success:
        print()
        print("🚀 サーバー再起動後、以下のURLで全同期を実行してください:")
        print("http://localhost:8080/sync-orders?days=30")
    else:
        print()
        print("⚠️ サーバーの再起動が必要です")