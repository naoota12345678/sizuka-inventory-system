"""
Playwright Test for Rakuten Order Sync API
最終動作確認テスト
"""

import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright, expect

API_URL = "https://rakuten-order-sync-7alvdxgvsa-an.a.run.app"

async def test_api():
    async with async_playwright() as p:
        # ブラウザの起動
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("=== Rakuten Order Sync API 最終チェック開始 ===")
        print(f"テスト実行時刻: {datetime.now()}")
        print(f"API URL: {API_URL}\n")
        
        try:
            # 1. ルートエンドポイントのテスト
            print("1. ルートエンドポイントのテスト...")
            response = await page.goto(API_URL)
            assert response.status == 200, f"ステータスコードが異常: {response.status}"
            
            root_data = await response.json()
            print(f"   ✓ レスポンス: {json.dumps(root_data, indent=2, ensure_ascii=False)}")
            assert root_data.get("message") == "Rakuten Order Sync API"
            assert root_data.get("version") == "1.0.0"
            print("   ✓ ルートエンドポイント: OK\n")
            
            # 2. ヘルスチェックエンドポイント
            print("2. ヘルスチェックエンドポイントのテスト...")
            response = await page.goto(f"{API_URL}/health")
            assert response.status == 200
            
            health_data = await response.json()
            print(f"   ✓ ヘルスステータス: {health_data.get('status')}")
            print(f"   ✓ Supabase接続: {health_data.get('supabase_connected')}")
            print(f"   ✓ DB Setup利用可能: {health_data.get('db_setup_available')}")
            print(f"   ✓ Sheets Sync利用可能: {health_data.get('sheets_sync_available')}")
            print("   ✓ ヘルスチェック: OK\n")
            
            # 3. データベース接続確認
            print("3. データベース接続確認のテスト...")
            response = await page.goto(f"{API_URL}/check-connection")
            assert response.status == 200
            
            db_data = await response.json()
            print(f"   ✓ 接続ステータス: {db_data.get('status')}")
            if db_data.get('platform'):
                print(f"   ✓ プラットフォーム情報: {len(db_data['platform'])}件")
            print(f"   ✓ 注文数: {db_data.get('orders_count', 0)}件")
            print(f"   ✓ 注文アイテム数: {db_data.get('items_count', 0)}件")
            print("   ✓ データベース接続: OK\n")
            
            # 4. APIドキュメントページ
            print("4. APIドキュメントページのテスト...")
            await page.goto(f"{API_URL}/docs")
            await page.wait_for_load_state('networkidle')
            
            # Swagger UIのタイトルを確認
            title = await page.text_content('h2.title')
            print(f"   ✓ APIドキュメントタイトル: {title}")
            
            # エンドポイントの数を確認
            endpoints = await page.locator('.opblock').count()
            print(f"   ✓ 利用可能なエンドポイント数: {endpoints}")
            
            # 各エンドポイントの概要を取得
            print("   ✓ エンドポイント一覧:")
            for i in range(min(endpoints, 10)):  # 最初の10個まで表示
                method = await page.locator(f'.opblock:nth-child({i+1}) .opblock-summary-method').text_content()
                path = await page.locator(f'.opblock:nth-child({i+1}) .opblock-summary-path').text_content()
                desc = await page.locator(f'.opblock:nth-child({i+1}) .opblock-summary-description').text_content()
                print(f"      - {method} {path}: {desc}")
            
            print("   ✓ APIドキュメント: OK\n")
            
            # 5. デバッグ環境情報
            print("5. デバッグ環境情報の確認...")
            response = await page.goto(f"{API_URL}/debug-env")
            assert response.status == 200
            
            debug_data = await response.json()
            print(f"   ✓ Google認証ファイル: {'設定済み' if debug_data.get('creds_file_found') else '未設定'}")
            print(f"   ✓ Spreadsheet ID: {'設定済み' if debug_data.get('spreadsheet_id_set') else '未設定'}")
            print(f"   ✓ 作業ディレクトリ: {debug_data.get('working_directory')}")
            print("   ✓ デバッグ環境: OK\n")
            
            # 6. 在庫ダッシュボード
            print("6. 在庫ダッシュボードのテスト...")
            response = await page.goto(f"{API_URL}/inventory-dashboard?low_stock_threshold=5")
            assert response.status == 200
            
            dashboard_data = await response.json()
            if dashboard_data.get('summary'):
                summary = dashboard_data['summary']
                print(f"   ✓ 総商品数: {summary.get('total_products', 0)}")
                print(f"   ✓ アクティブ商品数: {summary.get('active_products', 0)}")
                print(f"   ✓ 在庫切れ商品数: {summary.get('out_of_stock_count', 0)}")
                print(f"   ✓ 在庫少商品数: {summary.get('low_stock_count', 0)}")
            print("   ✓ 在庫ダッシュボード: OK\n")
            
            # スクリーンショットを保存
            await page.screenshot(path="api_test_screenshot.png", full_page=True)
            print("   ✓ スクリーンショットを保存しました: api_test_screenshot.png\n")
            
            print("=== すべてのテストが正常に完了しました ===")
            print("APIは正常に動作しています！")
            
        except Exception as e:
            print(f"\n❌ エラーが発生しました: {str(e)}")
            # エラー時のスクリーンショット
            await page.screenshot(path="api_test_error.png", full_page=True)
            print("   エラー時のスクリーンショットを保存しました: api_test_error.png")
            raise
            
        finally:
            await browser.close()

# テストの実行
if __name__ == "__main__":
    asyncio.run(test_api())
