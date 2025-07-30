@echo off
echo Checking Cloud Run logs...
echo.

echo === Recent logs ===
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=rakuten-order-sync" --limit=50 --format=json

echo.
echo === Checking for errors ===
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=rakuten-order-sync AND severity>=ERROR" --limit=20 --format=json

pause
