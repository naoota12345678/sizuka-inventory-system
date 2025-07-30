@echo off
echo === Cloud Buildのログを確認します ===
echo.

cd /d "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"

echo 最新のビルド情報を取得しています...
echo.
gcloud builds list --limit=1

echo.
echo === 最新のビルドIDを取得してログを表示 ===
echo.

REM 最新のビルドIDを取得
for /f "tokens=1" %%i in ('gcloud builds list --limit=1 --format="value(id)"') do set BUILD_ID=%%i

if "%BUILD_ID%"=="" (
    echo ビルドIDが見つかりません
    pause
    exit /b 1
)

echo ビルドID: %BUILD_ID%
echo.
echo 詳細なビルドログを表示します...
echo.

gcloud builds log %BUILD_ID% > build_log.txt 2>&1

REM エラーとWarningを抽出
echo === エラーとWarning ===
findstr /i "error warning" build_log.txt

echo.
echo === requirements.txt関連 ===
findstr /i "requirements" build_log.txt

echo.
echo === Google API関連 ===
findstr /i "google-api sheets" build_log.txt

echo.
echo === Cloud Runサービスログ ===
echo.
gcloud run services logs read rakuten-order-sync --region asia-northeast1 --limit 20 > service_log.txt 2>&1

echo === Sheets同期関連のログ ===
findstr /i "sheets google-api sync" service_log.txt

echo.
echo ログファイルを保存しました:
echo - build_log.txt (ビルドログ)
echo - service_log.txt (サービスログ)
echo.
pause