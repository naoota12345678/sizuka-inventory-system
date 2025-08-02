from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import requests

app = FastAPI()

@app.get("/api/debug_rakuten_auth")
def debug_rakuten_auth():
    """楽天API認証情報とアクセスをデバッグ"""
    try:
        # 環境変数の確認
        service_secret = os.getenv("RAKUTEN_SERVICE_SECRET")
        license_key = os.getenv("RAKUTEN_LICENSE_KEY")
        
        auth_status = {
            "service_secret_exists": bool(service_secret),
            "license_key_exists": bool(license_key),
            "service_secret_length": len(service_secret) if service_secret else 0,
            "license_key_length": len(license_key) if license_key else 0,
            "service_secret_prefix": service_secret[:10] + "..." if service_secret else None,
            "license_key_prefix": license_key[:10] + "..." if license_key else None
        }
        
        # 楽天APIへの実際のテスト接続
        if service_secret and license_key:
            try:
                # 楽天商品検索APIのテストコール
                test_url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
                test_params = {
                    "format": "json",
                    "keyword": "test",
                    "applicationId": license_key,
                    "hits": 1
                }
                
                response = requests.get(test_url, params=test_params, timeout=10)
                api_test = {
                    "status_code": response.status_code,
                    "response_size": len(response.text),
                    "success": response.status_code == 200,
                    "error_details": response.text[:200] if response.status_code != 200 else None
                }
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        api_test["has_items"] = "Items" in json_data
                        api_test["item_count"] = len(json_data.get("Items", []))
                    except:
                        api_test["json_parse_error"] = True
                        
            except Exception as e:
                api_test = {
                    "connection_error": True,
                    "error_message": str(e)
                }
        else:
            api_test = {"skipped": "Missing credentials"}
        
        # 楽天RMS API（商品管理API）のテスト
        rms_test = {"status": "not_implemented"}
        if service_secret and license_key:
            try:
                # 実際のAPIエンドポイントのテスト（実装が必要）
                rms_test = {
                    "service_secret_format": "SP" in service_secret,
                    "license_key_format": "SL" in license_key,
                    "credentials_format_valid": "SP" in service_secret and "SL" in license_key
                }
            except Exception as e:
                rms_test = {"error": str(e)}
        
        return {
            "status": "success",
            "authentication_check": auth_status,
            "rakuten_api_test": api_test,
            "rms_api_test": rms_test,
            "recommendations": [
                "環境変数が正しく設定されているか確認" if not auth_status["service_secret_exists"] or not auth_status["license_key_exists"] else "認証情報は設定済み",
                "楽天APIアクセス権限を確認" if api_test.get("status_code") != 200 else "楽天API接続は正常",
                "商品管理APIの実装を確認" if rms_test.get("status") == "not_implemented" else "RMS API確認済み"
            ]
        }
        
    except Exception as e:
        return {"status": "error", "message": f"デバッグエラー: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)