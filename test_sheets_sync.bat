@echo off
echo === Testing Google Sheets Sync ===
echo.

set BASE_URL=https://rakuten-order-sync-454314269549.asia-northeast1.run.app

echo Testing product master sync...
curl -X POST "%BASE_URL%/sync-product-master"
echo.
echo.

echo Checking health status...
curl -X GET "%BASE_URL%/health"
echo.
echo.

pause
