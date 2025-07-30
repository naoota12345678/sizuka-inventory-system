import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime

class RakutenOrderSyncTester:
    def __init__(self):
        self.base_url = "https://rakuten-order-sync-454314269549.asia-northeast1.run.app"
        self.test_results = []
        
    async def test_api_endpoints(self):
        """APIエンドポイントのテスト"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            print("🧪 Rakuten Order Sync API テスト開始")
            print("=" * 50)
            
            # 1. ルートエンドポイントのテスト
            await self.test_endpoint(page, "/", "GET", "ルートエンドポイント")
            
            # 2. ヘルスチェックのテスト
            await self.test_endpoint(page, "/health", "GET", "ヘルスチェック")
            
            # 3. APIドキュメントのテスト
            await self.test_api_docs(page)
            
            # 4. データベース接続のテスト
            await self.test_endpoint(page, "/check-connection", "GET", "データベース接続確認")
            
            # 5. データベースセットアップ確認
            await self.test_endpoint(page, "/check-database-setup", "GET", "データベースセットアップ確認")
            
            # 6. 注文同期のテスト（1日分）
            await self.test_endpoint(page, "/sync-orders?days=1", "GET", "注文同期（1日分）")
            
            # 7. 在庫ダッシュボードのテスト
            await self.test_endpoint(page, "/inventory-dashboard", "GET", "在庫ダッシュボード")
            
            # 8. 商品マスター同期のテスト
            await self.test_endpoint(page, "/sync-product-master", "POST", "商品マスター同期", expect_error=True)
            
            # テスト結果のサマリー
            await self.print_summary()
            
            await browser.close()
    
    async def test_endpoint(self, page, path, method="GET", test_name="", expect_error=False):
        """個別のエンドポイントをテスト"""
        url = f"{self.base_url}{path}"
        print(f"\n📍 テスト: {test_name}")
        print(f"   URL: {url}")
        print(f"   Method: {method}")
        
        try:
            if method == "GET":
                response = await page.goto(url)
            else:  # POST
                response = await page.request.post(url)
            
            status = response.status
            print(f"   Status: {status}")
            
            # レスポンスボディの取得
            try:
                if response.ok or status < 500:
                    body = await response.text()
                    data = json.loads(body)
                    print(f"   Response: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                    
                    # 特定のエンドポイントの詳細確認
                    if path == "/health":
                        self.analyze_health_check(data)
                    elif path == "/check-database-setup":
                        self.analyze_database_setup(data)
                    
                    success = not expect_error
                else:
                    success = expect_error
                    
            except Exception as e:
                print(f"   Response parsing error: {e}")
                success = expect_error
            
            self.test_results.append({
                "name": test_name,
                "url": url,
                "status": status,
                "success": success,
                "expect_error": expect_error
            })
            
            if success:
                print("   ✅ テスト成功")
            else:
                print("   ❌ テスト失敗")
                
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            self.test_results.append({
                "name": test_name,
                "url": url,
                "status": "Error",
                "success": False,
                "error": str(e)
            })
    
    async def test_api_docs(self, page):
        """APIドキュメントページのテスト"""
        print(f"\n📍 テスト: APIドキュメント")
        url = f"{self.base_url}/docs"
        print(f"   URL: {url}")
        
        try:
            await page.goto(url)
            await page.wait_for_selector("h2", timeout=5000)
            
            # Swagger UIのタイトルを確認
            title = await page.text_content("h2")
            print(f"   Title: {title}")
            
            # APIエンドポイントの数を確認
            endpoints = await page.query_selector_all(".opblock")
            print(f"   エンドポイント数: {len(endpoints)}")
            
            self.test_results.append({
                "name": "APIドキュメント",
                "url": url,
                "status": 200,
                "success": True,
                "endpoints_count": len(endpoints)
            })
            print("   ✅ テスト成功")
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            self.test_results.append({
                "name": "APIドキュメント",
                "url": url,
                "status": "Error",
                "success": False,
                "error": str(e)
            })
    
    def analyze_health_check(self, data):
        """ヘルスチェックの結果を分析"""
        print("\n   📊 ヘルスチェック詳細:")
        print(f"      - Supabase初期化: {'✅' if data.get('supabase_initialized') else '❌'}")
        print(f"      - DB Setup利用可能: {'✅' if data.get('db_setup_available') else '❌'}")
        print(f"      - Sheets Sync利用可能: {'✅' if data.get('sheets_sync_available') else '❌'}")
    
    def analyze_database_setup(self, data):
        """データベースセットアップの結果を分析"""
        print("\n   📊 データベースセットアップ詳細:")
        status = data.get('status', 'unknown')
        print(f"      - Status: {status}")
        
        if 'tables' in data:
            print("      - テーブル状態:")
            for table, exists in data['tables'].items():
                print(f"        • {table}: {'✅' if exists else '❌'}")
        
        if 'missing_tables' in data:
            missing = data['missing_tables']
            if missing:
                print(f"      - 不足テーブル: {', '.join(missing)}")
    
    async def print_summary(self):
        """テスト結果のサマリーを表示"""
        print("\n" + "=" * 50)
        print("📊 テスト結果サマリー")
        print("=" * 50)
        
        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r['success'])
        
        print(f"総テスト数: {total}")
        print(f"成功: {success}")
        print(f"失敗: {total - success}")
        print(f"成功率: {(success/total*100):.1f}%")
        
        print("\n詳細:")
        for result in self.test_results:
            status_icon = "✅" if result['success'] else "❌"
            status_text = result.get('status', 'N/A')
            print(f"{status_icon} {result['name']}: Status {status_text}")
            if 'error' in result:
                print(f"   Error: {result['error']}")
        
        # 結果をファイルに保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'base_url': self.base_url,
                'summary': {
                    'total': total,
                    'success': success,
                    'failed': total - success,
                    'success_rate': f"{(success/total*100):.1f}%"
                },
                'results': self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 テスト結果を {filename} に保存しました")

async def main():
    tester = RakutenOrderSyncTester()
    await tester.test_api_endpoints()

if __name__ == "__main__":
    asyncio.run(main())
