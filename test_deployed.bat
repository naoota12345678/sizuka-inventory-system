@echo off
echo 🧪 デプロイ済みAPIのテストを開始します...

:: 仮想環境をアクティベート
call venv\Scripts\activate

:: 最新のサービスURLを取得
for /f "tokens=*" %%i in ('gcloud run services describe rakuten-order-sync --region=asia-northeast1 --format="value(status.url)"') do set SERVICE_URL=%%i

if "%SERVICE_URL%"=="" (
    echo ❌ サービスURLが取得できませんでした
    pause
    exit /b 1
)

echo 📍 サービスURL: %SERVICE_URL%
echo.

:: APIテストを実行
python test_deployed_api.py %SERVICE_URL%

pause