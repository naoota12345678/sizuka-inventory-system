@echo off
echo Testing Rakuten Order Sync endpoints...
echo.

set BASE_URL=https://rakuten-order-sync-454314269549.asia-northeast1.run.app

echo === Testing Health Check ===
curl -X GET "%BASE_URL%/health"
echo.
echo.

echo === Testing Order Sync (1 day) ===
curl -X GET "%BASE_URL%/sync-orders?days=1"
echo.
echo.

echo === Testing Database Connection ===
curl -X GET "%BASE_URL%/check-connection"
echo.
echo.

echo === Testing Product Master Sync ===
curl -X POST "%BASE_URL%/sync-product-master"
echo.
echo.

echo === Testing Database Setup Check ===
curl -X GET "%BASE_URL%/check-database-setup"
echo.
echo.

pause
