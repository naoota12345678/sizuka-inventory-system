@echo off
echo Setting up Google Sheets authentication for Cloud Run...

:: Read google-credentials.json file content
echo Reading Google credentials file...
set /p CREDS=<google-credentials.json

:: Create secret with JSON content
echo Creating secret for Google credentials JSON...
echo %CREDS% | gcloud secrets create GOOGLE_CREDENTIALS_JSON --data-file=- 2>nul
if %errorlevel% neq 0 (
    echo Updating existing secret...
    echo %CREDS% | gcloud secrets versions add GOOGLE_CREDENTIALS_JSON --data-file=-
)

:: Update Cloud Run service
echo Updating Cloud Run service with Google credentials...
gcloud run services update rakuten-order-sync ^
  --region=asia-northeast1 ^
  --set-secrets="GOOGLE_CREDENTIALS_JSON=GOOGLE_CREDENTIALS_JSON:latest"

echo.
echo Configuration complete! Now redeploy the service:
echo gcloud builds submit --config=cloudbuild.yaml
echo.
pause