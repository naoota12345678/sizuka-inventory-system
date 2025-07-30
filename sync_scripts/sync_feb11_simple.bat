@echo off
echo ===================================================
echo 2/11以降の注文データ同期
echo ===================================================

set BASE_URL=https://rakuten-order-sync-454314269549.asia-northeast1.run.app

:: スプレッドシート同期
echo.
echo Step 1: Spreadsheet sync...
curl -X POST "%BASE_URL%/sync-sheets"
echo.

:: 待機
timeout /t 5 > nul

:: 注文同期
echo.
echo Step 2: Order sync (2025-02-11 to today)...
curl "%BASE_URL%/sync-orders-range?start_date=2025-02-11&end_date=2025-06-09"

echo.
echo ===================================================
echo Complete!
echo ===================================================
pause
