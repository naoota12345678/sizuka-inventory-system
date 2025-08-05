#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
platform_daily_salesテーブル作成
Phase 1: 新しい売上分析システムの基盤構築
"""

from supabase import create_client
import sys

SUPABASE_URL = "https://equrcpeifogdrxoldkpe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ"

def create_platform_sales_table():
    """platform_daily_salesテーブルを作成"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("=== platform_daily_salesテーブル作成 ===\n")
    
    # 1. 既存テーブル確認
    print("【1】既存テーブル確認")
    try:
        response = supabase.table("platform_daily_sales").select("*").limit(1).execute()
        print("⚠️  警告: platform_daily_salesテーブルが既に存在します")
        print(f"   既存データ件数: {len(response.data)}件")
        
        user_input = input("既存テーブルを削除して再作成しますか？ (y/N): ")
        if user_input.lower() != 'y':
            print("処理を中止しました")
            return False
        
        print("既存テーブルを削除中...")
        
    except Exception as e:
        if "does not exist" in str(e) or "relation" in str(e):
            print("✅ platform_daily_salesテーブルは存在しません（新規作成）")
        else:
            print(f"❌ テーブル確認エラー: {str(e)}")
            return False
    
    # 2. テーブル作成SQL
    print(f"\n【2】テーブル作成")
    
    create_table_sql = """
    -- platform_daily_sales テーブル作成
    CREATE TABLE IF NOT EXISTS platform_daily_sales (
        sales_date DATE NOT NULL,
        platform VARCHAR(20) NOT NULL,
        total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
        order_count INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        -- プライマリキー
        PRIMARY KEY (sales_date, platform),
        
        -- 制約
        CONSTRAINT valid_platform CHECK (platform IN ('rakuten', 'amazon', 'colorme', 'airegi', 'yahoo')),
        CONSTRAINT positive_amount CHECK (total_amount >= 0),
        CONSTRAINT positive_count CHECK (order_count >= 0)
    );
    
    -- インデックス作成
    CREATE INDEX IF NOT EXISTS idx_platform_sales_date ON platform_daily_sales(sales_date);
    CREATE INDEX IF NOT EXISTS idx_platform_sales_platform ON platform_daily_sales(platform);
    CREATE INDEX IF NOT EXISTS idx_platform_sales_amount ON platform_daily_sales(total_amount DESC);
    
    -- コメント追加
    COMMENT ON TABLE platform_daily_sales IS 'プラットフォーム別日次売上集計テーブル';
    COMMENT ON COLUMN platform_daily_sales.sales_date IS '売上日';
    COMMENT ON COLUMN platform_daily_sales.platform IS '販売プラットフォーム';
    COMMENT ON COLUMN platform_daily_sales.total_amount IS 'その日の売上合計金額';
    COMMENT ON COLUMN platform_daily_sales.order_count IS 'その日の注文件数';
    """
    
    try:
        # Supabaseでは直接SQLの実行ができないため、代替手段を検討
        print("Supabase環境ではSQL直接実行ができません。")
        print("以下の方法で手動作成をお願いします：")
        print("\n" + "="*60)
        print("Supabase Dashboard → SQL Editor で以下を実行:")
        print("="*60)
        print(create_table_sql)
        print("="*60)
        
        # 作成確認を待つ
        input("\nテーブル作成が完了したらEnterキーを押してください...")
        
    except Exception as e:
        print(f"❌ テーブル作成エラー: {str(e)}")
        return False
    
    # 3. 作成確認
    print(f"\n【3】作成確認")
    try:
        response = supabase.table("platform_daily_sales").select("*").limit(1).execute()
        print("✅ platform_daily_salesテーブルが正常に作成されました")
        
        # テスト データ挿入
        test_data = {
            "sales_date": "2025-08-04",
            "platform": "rakuten", 
            "total_amount": 100000,
            "order_count": 10
        }
        
        insert_response = supabase.table("platform_daily_sales").insert(test_data).execute()
        if insert_response.data:
            print("✅ テストデータの挿入が成功しました")
            
            # テストデータを削除
            supabase.table("platform_daily_sales").delete().eq("sales_date", "2025-08-04").eq("platform", "rakuten").execute()
            print("✅ テストデータを削除しました")
        else:
            print("⚠️  テストデータの挿入に失敗しました")
        
        return True
        
    except Exception as e:
        print(f"❌ 作成確認エラー: {str(e)}")
        print("テーブルが正しく作成されていない可能性があります")
        return False

def show_next_steps():
    """次のステップを表示"""
    print(f"\n" + "="*60)
    print("🎉 Phase 1 Step 1 完了!")
    print("="*60)
    print("✅ platform_daily_salesテーブル作成完了")
    print("\n次のステップ:")
    print("1. 楽天データからの日次集計処理作成")
    print("2. /api/sales/platform_summary API作成")
    print("3. 期間選択UI作成")
    print("="*60)

if __name__ == "__main__":
    print("Phase 1 Step 1: platform_daily_salesテーブル作成")
    print("="*60)
    
    success = create_platform_sales_table()
    
    if success:
        show_next_steps()
    else:
        print("\n❌ テーブル作成に失敗しました")
        print("問題を確認して再実行してください")
        sys.exit(1)