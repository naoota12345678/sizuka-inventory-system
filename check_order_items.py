import os
from supabase import create_client
from datetime import datetime

# Supabase接続
supabase_url = os.environ.get("SUPABASE_URL", "https://equrcpeifogdrxoldkpe.supabase.co")
supabase_key = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ")

supabase = create_client(supabase_url, supabase_key)

print("=== order_items テーブルの確認 ===\n")

# 1. 総件数を確認
response = supabase.table("order_items").select("id", count="exact").execute()
total_count = len(response.data) if response.data else 0
print(f"1. 総レコード数: {total_count}件\n")

# 2. 最新10件のデータを確認
print("2. 最新10件のデータ:")
response = supabase.table("order_items").select("*").order("created_at", desc=True).limit(10).execute()
for i, item in enumerate(response.data[:10], 1):
    print(f"\n--- {i}件目 ---")
    print(f"作成日時: {item.get('created_at', 'N/A')}")
    print(f"商品コード: {item.get('product_code', 'N/A')}")
    print(f"商品名: {item.get('product_name', 'N/A')[:50]}...")
    print(f"楽天SKU: {item.get('rakuten_sku', 'なし')}")
    print(f"選択肢コード: {item.get('choice_code', 'なし')}")
    print(f"数量: {item.get('quantity', 0)}")
    print(f"価格: {item.get('price', 0)}円")

# 3. 日付範囲を確認
print("\n\n3. データの日付範囲:")
# ordersテーブルと結合して注文日を確認
response = supabase.table("order_items").select("*, orders!inner(order_date)").execute()
if response.data:
    dates = [item['orders']['order_date'] for item in response.data if 'orders' in item and 'order_date' in item['orders']]
    if dates:
        dates.sort()
        print(f"最古の注文日: {dates[0]}")
        print(f"最新の注文日: {dates[-1]}")
        
        # 月別集計
        from collections import defaultdict
        monthly_count = defaultdict(int)
        for date_str in dates:
            month = date_str[:7]  # YYYY-MM形式
            monthly_count[month] += 1
        
        print("\n月別データ件数:")
        for month, count in sorted(monthly_count.items()):
            print(f"  {month}: {count}件")

# 4. SKUと選択肢コードの充実度
print("\n\n4. データの充実度:")
response = supabase.table("order_items").select("rakuten_sku, choice_code").execute()
if response.data:
    sku_count = len([item for item in response.data if item.get('rakuten_sku')])
    choice_count = len([item for item in response.data if item.get('choice_code')])
    
    print(f"SKUコード登録済み: {sku_count}件 ({sku_count/len(response.data)*100:.1f}%)")
    print(f"選択肢コード登録済み: {choice_count}件 ({choice_count/len(response.data)*100:.1f}%)")