#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Sheets同期機能のテストスクリプト
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any

class SheetsSyncTester:
    def __init__(self):
        self.base_url = "https://rakuten-order-sync-454314269549.asia-northeast1.run.app"
        self.local_url = "http://localhost:8080"
        self.test_results = []
        
    async def test_endpoints(self, use_local=False):
        """Google Sheets関連のエンドポイントをテスト"""
        url = self.local_url if use_local else self.base_url
        print(f"🧪 Google Sheets同期テストを開始します")
        print(f"   対象URL: {url}")
        print("=" * 60)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. 環境変数の確認
            await self.test_debug_env(client, url)
            
            # 2. ヘルスチェック
            await self.test_health_check(client, url)
            
            # 3. データベースセットアップ確認
            await self.test_database_setup(client, url)
            
            # 4. 商品マスター同期テスト
            await self.test_sync_product_master(client, url)
            
            # 5. 結果サマリー
            self.print_summary()
    
    async def test_debug_env(self, client: httpx.AsyncClient, base_url: str):
        """環境変数の確認"""
        print("\n📍 環境変数の確認")
        try:
            response = await client.get(f"{base_url}/debug-env")
            data = response.json()
            
            print(f"   Status: {response.status_code}")
            print(f"   Google認証環境変数: {data.get('google_creds_env', 'Not set')}")
            print(f"   ファイル存在: {'✅' if data.get('file_exists') else '❌'}")
            print(f"   Sheets Sync利用可能: {'✅' if data.get('sheets_sync_available') else '❌'}")
            
            if data.get('file_exists'):
                print(f"   ファイルサイズ: {data.get('file_size', 0)} bytes")
            
            self.test_results.append({
                "name": "環境変数確認",
                "success": data.get('sheets_sync_available', False),
                "details": data
            })
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            self.test_results.append({
                "name": "環境変数確認",
                "success": False,
                "error": str(e)
            })
    
    async def test_health_check(self, client: httpx.AsyncClient, base_url: str):
        """ヘルスチェック"""
        print("\n📍 ヘルスチェック")
        try:
            response = await client.get(f"{base_url}/health")
            data = response.json()
            
            print(f"   Status: {response.status_code}")
            print(f"   Supabase: {'✅' if data.get('supabase_initialized') else '❌'}")
            print(f"   DB Setup: {'✅' if data.get('db_setup_available') else '❌'}")
            print(f"   Sheets Sync: {'✅' if data.get('sheets_sync_available') else '❌'}")
            
            self.test_results.append({
                "name": "ヘルスチェック",
                "success": response.status_code == 200,
                "details": data
            })
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            self.test_results.append({
                "name": "ヘルスチェック",
                "success": False,
                "error": str(e)
            })
    
    async def test_database_setup(self, client: httpx.AsyncClient, base_url: str):
        """データベースセットアップ確認"""
        print("\n📍 データベースセットアップ確認")
        try:
            response = await client.get(f"{base_url}/check-database-setup")
            data = response.json()
            
            print(f"   Status: {response.status_code}")
            print(f"   セットアップ状態: {data.get('status', 'unknown')}")
            
            if 'tables' in data:
                print("   テーブル状態:")
                for table, exists in data['tables'].items():
                    if table in ['product_master', 'choice_code_mapping', 'package_components']:
                        print(f"     • {table}: {'✅' if exists else '❌'}")
            
            if 'missing_tables' in data and data['missing_tables']:
                print(f"   ⚠️ 不足テーブル: {', '.join(data['missing_tables'])}")
            
            self.test_results.append({
                "name": "データベースセットアップ",
                "success": data.get('status') == 'ok',
                "details": data
            })
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            self.test_results.append({
                "name": "データベースセットアップ",
                "success": False,
                "error": str(e)
            })
    
    async def test_sync_product_master(self, client: httpx.AsyncClient, base_url: str):
        """商品マスター同期テスト"""
        print("\n📍 商品マスター同期テスト")
        try:
            response = await client.post(f"{base_url}/sync-product-master", timeout=60.0)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   結果: {data.get('message', '')}")
                
                if 'results' in data:
                    results = data['results']
                    print("\n   同期結果詳細:")
                    
                    # 商品マスター
                    pm = results.get('product_master', {})
                    print(f"     商品マスター: 成功 {pm.get('success', 0)}件, エラー {pm.get('error', 0)}件")
                    
                    # 選択肢コード
                    cc = results.get('choice_codes', {})
                    print(f"     選択肢コード: 成功 {cc.get('success', 0)}件, エラー {cc.get('error', 0)}件")
                    
                    # まとめ商品内訳
                    pc = results.get('package_components', {})
                    print(f"     まとめ商品内訳: 成功 {pc.get('success', 0)}件, エラー {pc.get('error', 0)}件")
                
                self.test_results.append({
                    "name": "商品マスター同期",
                    "success": True,
                    "details": data
                })
            else:
                error_data = response.json()
                print(f"   ❌ エラー: {error_data.get('detail', 'Unknown error')}")
                self.test_results.append({
                    "name": "商品マスター同期",
                    "success": False,
                    "error": error_data.get('detail', 'Unknown error')
                })
                
        except httpx.TimeoutException:
            print(f"   ⏱️ タイムアウト: 60秒を超えました")
            self.test_results.append({
                "name": "商品マスター同期",
                "success": False,
                "error": "Timeout after 60 seconds"
            })
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            self.test_results.append({
                "name": "商品マスター同期",
                "success": False,
                "error": str(e)
            })
    
    def print_summary(self):
        """テスト結果のサマリー表示"""
        print("\n" + "=" * 60)
        print("📊 テスト結果サマリー")
        print("=" * 60)
        
        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r.get('success', False))
        
        print(f"総テスト数: {total}")
        print(f"成功: {success}")
        print(f"失敗: {total - success}")
        print(f"成功率: {(success/total*100):.1f}%" if total > 0 else "N/A")
        
        print("\n詳細:")
        for result in self.test_results:
            status_icon = "✅" if result.get('success', False) else "❌"
            print(f"{status_icon} {result['name']}")
            if 'error' in result:
                print(f"   Error: {result['error']}")
        
        # 結果をファイルに保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sheets_sync_test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'summary': {
                    'total': total,
                    'success': success,
                    'failed': total - success,
                    'success_rate': f"{(success/total*100):.1f}%" if total > 0 else "N/A"
                },
                'results': self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 テスト結果を {filename} に保存しました")

async def main():
    import sys
    
    # コマンドライン引数でローカルテストを指定可能
    use_local = "--local" in sys.argv
    
    tester = SheetsSyncTester()
    await tester.test_endpoints(use_local=use_local)

if __name__ == "__main__":
    asyncio.run(main())