@echo off
echo Setting up Google Sheets authentication...

:: Read google-credentials.json file and store in Secret Manager
echo Creating secret for Google credentials...
gcloud secrets create GOOGLE_CREDENTIALS_JSON --data-file=google-credentials.json 2>nul || echo Secret already exists

:: Update Cloud Run service with the secret
echo Updating Cloud Run service with Google credentials...
gcloud run services update rakuten-order-sync ^
  --region=asia-northeast1 ^
  --set-secrets="GOOGLE_CREDENTIALS_JSON=GOOGLE_CREDENTIALS_JSON:latest" ^
  --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/tmp/credentials.json"

echo Done! Redeploy the service to apply changes.
pause