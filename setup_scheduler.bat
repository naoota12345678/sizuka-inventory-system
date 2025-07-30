@echo off
echo Setting up Cloud Scheduler...

:: Get the service URL
for /f "tokens=*" %%i in ('gcloud run services describe rakuten-order-sync --region=asia-northeast1 --format="value(status.url)"') do set SERVICE_URL=%%i

:: Get project number
for /f "tokens=*" %%i in ('gcloud projects describe sizuka-syouhin --format="value(projectNumber)"') do set PROJECT_NUMBER=%%i
set SERVICE_ACCOUNT=%PROJECT_NUMBER%-compute@developer.gserviceaccount.com

:: Grant invoker permission
echo Granting permissions...
gcloud run services add-iam-policy-binding rakuten-order-sync ^
  --region=asia-northeast1 ^
  --member="serviceAccount:%SERVICE_ACCOUNT%" ^
  --role="roles/run.invoker"

:: Create scheduler job for daily sync
echo Creating scheduler job...
gcloud scheduler jobs create http daily-rakuten-sync ^
  --location=asia-northeast1 ^
  --schedule="0 2 * * *" ^
  --uri="%SERVICE_URL%/sync-orders?days=1" ^
  --http-method=GET ^
  --oidc-service-account-email="%SERVICE_ACCOUNT%" ^
  --time-zone="Asia/Tokyo" ^
  --description="Daily Rakuten order sync at 2AM JST"

:: Create scheduler job for product master sync (if needed)
echo Creating product master sync job...
gcloud scheduler jobs create http daily-product-master-sync ^
  --location=asia-northeast1 ^
  --schedule="30 1 * * *" ^
  --uri="%SERVICE_URL%/sync-product-master" ^
  --http-method=POST ^
  --oidc-service-account-email="%SERVICE_ACCOUNT%" ^
  --time-zone="Asia/Tokyo" ^
  --description="Daily product master sync at 1:30AM JST"

echo Scheduler setup completed!
echo.
echo Scheduled jobs:
echo - Daily order sync: 2:00 AM JST
echo - Daily product master sync: 1:30 AM JST
echo.
echo Service URL: %SERVICE_URL%
