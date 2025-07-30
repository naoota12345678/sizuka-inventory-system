@echo off
echo Creating Google Service Account JSON secret...

:: First, let's check if the secret already exists
gcloud secrets describe GOOGLE_SERVICE_ACCOUNT_JSON 2>nul
if %errorlevel% equ 0 (
    echo Secret already exists. Adding new version...
    type google-credentials.json | gcloud secrets versions add GOOGLE_SERVICE_ACCOUNT_JSON --data-file=-
) else (
    echo Creating new secret...
    type google-credentials.json | gcloud secrets create GOOGLE_SERVICE_ACCOUNT_JSON --data-file=-
)

echo.
echo Updating Cloud Run service...
gcloud run services update rakuten-order-sync --region=asia-northeast1 --set-secrets=GOOGLE_SERVICE_ACCOUNT_JSON=GOOGLE_SERVICE_ACCOUNT_JSON:latest

echo.
echo Done! Now redeploy the service:
echo gcloud builds submit --config=cloudbuild.yaml
pause