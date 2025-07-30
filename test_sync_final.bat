@echo off
echo === Testing Google Sheets Sync ===
echo.

echo 1. Testing product master sync...
curl -X POST "https://rakuten-order-sync-454314269549.asia-northeast1.run.app/sync-product-master" ^
  -H "Content-Type: application/json" ^
  -H "Content-Length: 0" ^
  -v

echo.
echo.
echo 2. Re-checking health status...
curl -X GET "https://rakuten-order-sync-454314269549.asia-northeast1.run.app/health"

echo.
echo.
pause
