@echo off
echo === Checking Deployment Status ===
echo.

echo 1. Getting latest logs...
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=rakuten-order-sync" --limit=20 --format="value(textPayload)"

echo.
echo 2. Testing product master sync...
curl -X POST "https://rakuten-order-sync-454314269549.asia-northeast1.run.app/sync-product-master" ^
  -H "Content-Type: application/json" ^
  -H "Content-Length: 0"

echo.
echo 3. Checking if credentials file exists in container...
echo (This would require shell access to the container)
echo.

pause
