#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プラットフォーム別売上集計API統合テスト
"""

import requests
import json

def test_platform_api():
    """APIエンドポイントのテスト"""
    
    # Cloud Run URL（デプロイ後はこれを使用）
    cloud_run_url = "https://sizuka-inventory-system-p2wv4efvja-an.a.run.app"
    
    # ローカルテスト用（必要に応じて変更）
    local_url = "http://localhost:8000"
    
    # 今回はCloud Run URLを使用
    base_url = cloud_run_url
    endpoint = "/api/sales/platform_summary"
    
    print("=== プラットフォーム別売上集計API統合テスト ===\n")
    
    # テスト1: パラメータなし（デフォルト: 過去30日）
    print("【テスト1】パラメータなし（過去30日）")
    try:
        response = requests.get(f"{base_url}{endpoint}")
        data = response.json()
        
        if response.status_code == 200 and data.get('status') == 'success':
            print(f"✅ 成功")
            print(f"   期間: {data['period']['start_date']} ~ {data['period']['end_date']}")
            print(f"   総売上: {data['total_sales']:,.0f}円")
            print(f"   プラットフォーム数: {len(data['platform_breakdown'])}個")
        else:
            print(f"❌ 失敗: {response.status_code}")
            print(f"   {data}")
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
    
    print("\n" + "-" * 50 + "\n")
    
    # テスト2: 期間指定
    print("【テスト2】期間指定（2025-07-01 ~ 2025-08-04）")
    try:
        params = {
            "start_date": "2025-07-01",
            "end_date": "2025-08-04"
        }
        response = requests.get(f"{base_url}{endpoint}", params=params)
        data = response.json()
        
        if response.status_code == 200 and data.get('status') == 'success':
            print(f"✅ 成功")
            print(f"   期間: {data['period']['start_date']} ~ {data['period']['end_date']}")
            print(f"   総売上: {data['total_sales']:,.0f}円")
            
            print(f"\n   プラットフォーム別内訳:")
            for platform, amount in data['platform_breakdown'].items():
                percentage = (amount / data['total_sales'] * 100) if data['total_sales'] > 0 else 0
                print(f"     {platform}: {amount:,.0f}円 ({percentage:.1f}%)")
            
            if 'daily_trends' in data and data['daily_trends']:
                print(f"\n   日別推移（最新3日）:")
                for trend in data['daily_trends'][-3:]:
                    print(f"     {trend['date']}: {trend['total']:,.0f}円")
        else:
            print(f"❌ 失敗: {response.status_code}")
            print(f"   {data}")
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
    
    print("\n" + "=" * 50)
    print("テスト完了")
    print("\n注意: Cloud Runへのデプロイが必要です")
    print("デプロイコマンド: gcloud run deploy sizuka-inventory-system ...")

if __name__ == "__main__":
    test_platform_api()