@echo off
echo === Testing Google Sheets Sync ===
echo.

set BASE_URL=https://rakuten-order-sync-454314269549.asia-northeast1.run.app

echo 1. Checking health status...
curl -X GET "%BASE_URL%/health"
echo.
echo.

echo 2. Testing product master sync (with proper headers)...
curl -X POST "%BASE_URL%/sync-product-master" ^
  -H "Content-Type: application/json" ^
  -H "Content-Length: 0"
echo.
echo.

echo 3. Checking if tables exist...
curl -X GET "%BASE_URL%/check-database-setup"
echo.
echo.

echo 4. Waiting for service to update (30 seconds)...
timeout /t 30

echo.
echo 5. Re-checking health status...
curl -X GET "%BASE_URL%/health"
echo.
echo.

pause
