@echo off
echo === Complete Google Sheets Setup ===
echo.

echo 1. Checking if credentials file exists...
if not exist google-credentials.json (
    echo Creating new credentials file...
    gcloud iam service-accounts keys create google-credentials.json ^
      --iam-account=rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com
) else (
    echo Found existing google-credentials.json
)

echo.
echo 2. Creating secret in Secret Manager...
gcloud secrets create google-sheets-credentials --data-file=google-credentials.json 2>nul
if %errorlevel% neq 0 (
    echo Secret may already exist. Let's delete and recreate...
    gcloud secrets delete google-sheets-credentials --quiet 2>nul
    gcloud secrets create google-sheets-credentials --data-file=google-credentials.json
)

echo.
echo 3. Granting access permissions...
echo - To Cloud Run default service account...
gcloud secrets add-iam-policy-binding google-sheets-credentials ^
  --member="serviceAccount:454314269549-compute@developer.gserviceaccount.com" ^
  --role="roles/secretmanager.secretAccessor"

echo - To custom service account...
gcloud secrets add-iam-policy-binding google-sheets-credentials ^
  --member="serviceAccount:rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com" ^
  --role="roles/secretmanager.secretAccessor"

echo.
echo 4. Verifying secret...
gcloud secrets versions list google-sheets-credentials

echo.
echo 5. Deploying with simpler configuration first...
gcloud run deploy rakuten-order-sync ^
  --source . ^
  --region asia-northeast1 ^
  --allow-unauthenticated ^
  --memory 1Gi ^
  --timeout 300 ^
  --set-env-vars="RAKUTEN_SERVICE_SECRET=SP338531_d1NJjF2R5OwZpWH6" ^
  --set-env-vars="RAKUTEN_LICENSE_KEY=SL338531_kUvqO4kIHaMbr9ik" ^
  --set-env-vars="SUPABASE_URL=https://equrcpeifogdrxoldkpe.supabase.co" ^
  --set-env-vars="SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVxdXJjcGVpZm9nZHJ4b2xka3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkxNjE2NTMsImV4cCI6MjA1NDczNzY1M30.ywOqf2BSf2PcIni5_tjJdj4p8E51jxBSrfD8BE8PAhQ" ^
  --set-env-vars="PRODUCT_MASTER_SPREADSHEET_ID=1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E"

echo.
echo 6. Now updating with secret mount...
gcloud run services update rakuten-order-sync ^
  --region=asia-northeast1 ^
  --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json" ^
  --set-secrets="/app/credentials.json=google-sheets-credentials:latest"

echo.
echo Setup completed!
pause
