import requests
import json
from datetime import datetime, timedelta

BASE_URL = "https://rakuten-order-sync-454314269549.asia-northeast1.run.app"

def sync_date_range(start_date, end_date):
    """指定された日付範囲の注文を同期"""
    print(f"\n📅 {start_date} から {end_date} の注文を同期中...")
    
    try:
        # 1. スプレッドシートと同期
        print("ステップ1: スプレッドシートと同期...")
        response = requests.post(f"{BASE_URL}/sync-sheets")
        if response.status_code == 200:
            print("✅ スプレッドシート同期成功")
        else:
            print(f"❌ スプレッドシート同期エラー: {response.status_code}")
            
        # 2. 注文を同期
        print(f"\nステップ2: 注文を同期...")
        response = requests.get(
            f"{BASE_URL}/sync-orders-range",
            params={
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 同期成功: {data}")
        else:
            print(f"❌ エラー: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ エラー: {e}")

def sync_by_chunks(start_date_str, end_date_str, chunk_days=7):
    """大量のデータを分割して同期（デフォルト: 7日ごと）"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    print(f"📊 {start_date_str} から {end_date_str} までの注文を{chunk_days}日ごとに分割して同期します")
    
    current_date = start_date
    while current_date < end_date:
        chunk_end = min(current_date + timedelta(days=chunk_days-1), end_date)
        
        sync_date_range(
            current_date.strftime("%Y-%m-%d"),
            chunk_end.strftime("%Y-%m-%d")
        )
        
        current_date = chunk_end + timedelta(days=1)
    
    print("\n✅ すべての同期が完了しました！")

if __name__ == "__main__":
    # 2月11日から今日まで同期
    # 一度に同期する場合
    # sync_date_range("2025-02-11", "2025-06-09")
    
    # 7日ごとに分割して同期する場合（推奨）
    sync_by_chunks("2025-02-11", "2025-06-09", chunk_days=7)
