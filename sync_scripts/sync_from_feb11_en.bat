@echo off
echo ===================================================
echo Sync orders from Feb 11, 2025
echo ===================================================

set BASE_URL=https://rakuten-order-sync-454314269549.asia-northeast1.run.app

:: Sync with spreadsheet first
echo.
echo Step 1: Syncing with Google Sheets...
curl -X POST "%BASE_URL%/sync-sheets"
echo.

:: Wait a moment
timeout /t 5

:: Sync orders from Feb 11 to today
echo.
echo Step 2: Syncing orders from 2025-02-11 to today...
curl "%BASE_URL%/sync-orders-range?start_date=2025-02-11&end_date=2025-06-09"

echo.
echo ===================================================
echo Sync completed!
echo ===================================================
pause
