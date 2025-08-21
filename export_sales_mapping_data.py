#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
売上データとマッピングテーブルをCSVでエクスポート
外部処理用のデータ抽出
"""

import os
import pandas as pd
from supabase import create_client
from datetime import datetime

# 環境変数設定
os.environ['SUPABASE_URL'] = 'https://equrcpeifogdrxoldkpe.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ'

# Supabase接続
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

def export_sales_data():
    """売上データをCSVでエクスポート"""
    print("=== 売上データエクスポート開始 ===")
    
    try:
        # 売上データを取得（全件）
        result = supabase.table('order_items').select(
            'quantity, product_code, choice_code, product_name, order_id'
        ).limit(16676).execute()
        
        print(f"取得した売上アイテム数: {len(result.data)}件")
        
        # DataFrameに変換
        df_sales = pd.DataFrame(result.data)
        
        # CSVファイルに保存
        csv_path = 'sales_data.csv'
        df_sales.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"売上データをCSVに保存: {csv_path}")
        
        # データの概要表示
        print(f"\n売上データ概要:")
        print(f"  - 総アイテム数: {len(df_sales)}件")
        print(f"  - 総数量: {df_sales['quantity'].sum():,}個")
        print(f"  - ユニーク商品コード数: {df_sales['product_code'].nunique()}件")
        print(f"  - 選択肢コードあり: {df_sales['choice_code'].notna().sum()}件")
        
        return csv_path
        
    except Exception as e:
        print(f"売上データエクスポートエラー: {str(e)}")
        return None

def export_mapping_tables():
    """マッピングテーブルをCSVでエクスポート"""
    print("\n=== マッピングテーブルエクスポート開始 ===")
    
    try:
        # product_masterテーブル
        pm_result = supabase.table('product_master').select('*').execute()
        df_pm = pd.DataFrame(pm_result.data)
        pm_path = 'product_master.csv'
        df_pm.to_csv(pm_path, index=False, encoding='utf-8-sig')
        print(f"商品マスタをCSVに保存: {pm_path} ({len(df_pm)}件)")
        
        # choice_code_mappingテーブル
        ccm_result = supabase.table('choice_code_mapping').select('*').execute()
        df_ccm = pd.DataFrame(ccm_result.data)
        ccm_path = 'choice_code_mapping.csv'
        df_ccm.to_csv(ccm_path, index=False, encoding='utf-8-sig')
        print(f"選択肢コードマッピングをCSVに保存: {ccm_path} ({len(df_ccm)}件)")
        
        return pm_path, ccm_path
        
    except Exception as e:
        print(f"マッピングテーブルエクスポートエラー: {str(e)}")
        return None, None

def export_current_inventory():
    """現在の在庫データをCSVでエクスポート"""
    print("\n=== 現在在庫データエクスポート開始 ===")
    
    try:
        # 現在の在庫データ
        inv_result = supabase.table('inventory').select('*').execute()
        df_inv = pd.DataFrame(inv_result.data)
        inv_path = 'current_inventory.csv'
        df_inv.to_csv(inv_path, index=False, encoding='utf-8-sig')
        
        total_stock = df_inv['current_stock'].sum()
        print(f"現在在庫をCSVに保存: {inv_path}")
        print(f"  - 在庫アイテム数: {len(df_inv)}件")
        print(f"  - 総在庫数: {total_stock:,}個")
        
        return inv_path
        
    except Exception as e:
        print(f"在庫データエクスポートエラー: {str(e)}")
        return None

def main():
    """メイン処理"""
    print("外部マッピング処理用データエクスポート")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: 売上データエクスポート
    sales_path = export_sales_data()
    
    # Step 2: マッピングテーブルエクスポート
    pm_path, ccm_path = export_mapping_tables()
    
    # Step 3: 現在在庫エクスポート
    inv_path = export_current_inventory()
    
    print("\n" + "=" * 60)
    print("エクスポート完了サマリー")
    print("=" * 60)
    
    if all([sales_path, pm_path, ccm_path, inv_path]):
        print("✅ 全データのエクスポートが完了しました")
        print("\n作成されたファイル:")
        print(f"  1. {sales_path} - 売上データ（16,676件）")
        print(f"  2. {pm_path} - 商品マスタ")
        print(f"  3. {ccm_path} - 選択肢コードマッピング")
        print(f"  4. {inv_path} - 現在在庫データ")
        
        print("\n次の手順:")
        print("1. Excel/Google Sheetsで外部マッピング実行")
        print("2. VLOOKUP/INDEX+MATCHで商品コード→共通コード変換")
        print("3. 在庫減少量を計算")
        print("4. 結果をCSVで保存")
        print("5. Supabaseに在庫更新結果をインポート")
        
        return True
    else:
        print("❌ 一部のエクスポートでエラーが発生しました")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 データエクスポートが完了しました！")
            print("外部ツールでマッピング処理を開始してください。")
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()