@echo off
echo Checking Cloud Scheduler jobs...
echo.

echo === List all scheduler jobs ===
gcloud scheduler jobs list --location=asia-northeast1

echo.
echo === Testing daily-rakuten-sync job ===
gcloud scheduler jobs run daily-rakuten-sync --location=asia-northeast1

echo.
echo === Testing daily-product-master-sync job ===
gcloud scheduler jobs run daily-product-master-sync --location=asia-northeast1

echo.
echo Tests initiated. Check the logs for results.
pause
