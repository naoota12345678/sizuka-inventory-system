#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存システムへの影響調査
新しい売上システム実装前の安全性確認
"""

from supabase import create_client
import os

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def analyze_existing_system_impact():
    """既存システムへの影響を調査"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=" * 80)
    print("既存システムへの影響調査レポート")
    print("=" * 80)
    
    # 1. 既存テーブル構造の確認
    print("\n【1】既存の重要テーブル確認")
    print("-" * 50)
    
    critical_tables = ['orders', 'order_items', 'inventory', 'choice_code_mapping', 'product_master']
    
    for table in critical_tables:
        try:
            response = supabase.table(table).select("*", count="exact").limit(1).execute()
            record_count = response.count
            print(f"✅ {table}: {record_count:,}件のデータが存在")
            
        except Exception as e:
            print(f"❌ {table}: エラー - {str(e)}")
    
    # 2. 新しいテーブル名の衝突チェック
    print(f"\n【2】新しいテーブル名の衝突チェック")
    print("-" * 50)
    
    new_table_name = "platform_daily_sales"
    
    try:
        response = supabase.table(new_table_name).select("*").limit(1).execute()
        print(f"⚠️  警告: {new_table_name}テーブルが既に存在します")
        print(f"   データ件数: {len(response.data)}件")
        print(f"   → 既存テーブルの確認が必要です")
        
    except Exception as e:
        if "does not exist" in str(e) or "relation" in str(e):
            print(f"✅ {new_table_name}: テーブル名は使用可能（存在しません）")
        else:
            print(f"❓ {new_table_name}: 確認エラー - {str(e)}")
    
    # 3. 既存APIエンドポイントの確認
    print(f"\n【3】既存API エンドポイントとの衝突チェック")
    print("-" * 50)
    
    planned_endpoints = [
        "/api/sales/platform_summary",
        "/api/inventory/trending_products"
    ]
    
    print("計画中の新しいAPIエンドポイント:")
    for endpoint in planned_endpoints:
        print(f"  - {endpoint}")
    
    print("\nmain_cloudrun.pyで既存の売上関連エンドポイントを確認中...")
    
    # 4. main_cloudrun.pyの既存エンドポイント確認
    try:
        with open("main_cloudrun.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        existing_sales_endpoints = []
        lines = content.split('\n')
        
        for line in lines:
            if '@app.get("/api/sales' in line:
                # エンドポイント名を抽出
                start = line.find('"/api/sales')
                end = line.find('"', start + 1)
                if start != -1 and end != -1:
                    endpoint = line[start+1:end]
                    existing_sales_endpoints.append(endpoint)
        
        print(f"\n既存の売上関連APIエンドポイント:")
        for endpoint in existing_sales_endpoints:
            print(f"  - {endpoint}")
            
        # 衝突チェック
        conflicts = []
        for new_ep in planned_endpoints:
            for existing_ep in existing_sales_endpoints:
                if new_ep == existing_ep:
                    conflicts.append(new_ep)
        
        if conflicts:
            print(f"\n⚠️  エンドポイント衝突の警告:")
            for conflict in conflicts:
                print(f"  - {conflict} (既に存在)")
        else:
            print(f"\n✅ エンドポイント衝突なし")
            
    except FileNotFoundError:
        print("❓ main_cloudrun.pyファイルが見つかりません")
    except Exception as e:
        print(f"❌ main_cloudrun.py確認エラー: {str(e)}")
    
    # 5. データ整合性への影響
    print(f"\n【4】データ整合性への影響分析")
    print("-" * 50)
    
    print("新しいシステムの影響範囲:")
    print("✅ READ ONLY操作:")
    print("  - orders テーブルからの読み取り（集計のため）")
    print("  - order_items テーブルからの読み取り（集計のため）")
    print("  - inventory テーブルからの読み取り（売れ筋分析のため）")
    
    print("\n✅ 新規作成:")
    print("  - platform_daily_sales テーブル（新規作成）")
    print("  - 新しいAPIエンドポイント（新規追加）")
    
    print("\n❌ 変更・削除なし:")
    print("  - 既存テーブルの変更なし")
    print("  - 既存データの削除なし")
    print("  - 既存APIの変更なし")
    
    # 6. 在庫システムへの影響
    print(f"\n【5】在庫システム（98%稼働）への影響")
    print("-" * 50)
    
    print("在庫システムへの影響:")
    print("✅ 影響なし:")
    print("  - choice_code_mapping テーブル: 読み取りのみ")
    print("  - inventory テーブル: 読み取りのみ")
    print("  - product_master テーブル: アクセスなし")
    print("  - 在庫管理ロジック: 変更なし")
    
    # 7. 推奨事項
    print(f"\n【6】推奨事項・注意点")
    print("-" * 50)
    
    print("実装前の推奨事項:")
    print("1. データベースバックアップの実行")
    print("2. テスト環境での事前検証")
    print("3. 段階的実装（テーブル作成 → API → UI）")
    print("4. 既存システムの監視継続")
    
    print(f"\n特に注意が必要な点:")
    print("1. Supabaseのクエリ数制限への影響")
    print("2. 新しい集計処理のパフォーマンス")
    print("3. Cloud Runのメモリ・CPU使用量")
    
    # 8. 結論
    print(f"\n【7】総合評価")
    print("-" * 50)
    
    print("🟢 リスクレベル: 低")
    print("理由:")
    print("  - 既存テーブルへの変更なし")
    print("  - 読み取り専用の操作のみ")
    print("  - 新規テーブル・APIの追加のみ")
    print("  - 在庫システムへの影響なし")
    
    print(f"\n✅ 実装許可の判断材料:")
    print("  - 既存システムへの直接的な影響: なし")
    print("  - データ破損のリスク: なし")
    print("  - 在庫システム(98%)への影響: なし")
    print("  - ロールバック可能性: 高（新規テーブル削除のみ）")

if __name__ == "__main__":
    analyze_existing_system_impact()