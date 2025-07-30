import httpx
import asyncio
import json

async def test_sheets_sync():
    """Google Sheets同期機能をテスト"""
    base_url = "https://rakuten-order-sync-454314269549.asia-northeast1.run.app"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🧪 Google Sheets同期テストを開始します")
        print("=" * 60)
        
        # 1. 環境変数の確認
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
        except Exception as e:
            print(f"   ❌ エラー: {e}")
        
        # 2. 商品マスター同期テスト
        print("\n📍 商品マスター同期テスト")
        try:
            print("   POSTリクエストを送信しています...")
            response = await client.post(f"{base_url}/sync-product-master")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 成功: {data.get('message', '')}")
                
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
            else:
                error_data = response.json()
                print(f"   ❌ エラー: {error_data.get('detail', 'Unknown error')}")
                print(f"   Response: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                
        except httpx.TimeoutException:
            print(f"   ⏱️ タイムアウト: 60秒を超えました")
        except Exception as e:
            print(f"   ❌ エラー: {e}")
        
        print("\n" + "=" * 60)
        print("テスト完了")

if __name__ == "__main__":
    asyncio.run(test_sheets_sync())