@echo off
echo === Fixing Secret Access Permissions ===
echo.

echo 1. Granting Secret Manager access to Cloud Run default service account...
gcloud secrets add-iam-policy-binding google-sheets-credentials ^
  --member="serviceAccount:454314269549-compute@developer.gserviceaccount.com" ^
  --role="roles/secretmanager.secretAccessor"

echo.
echo 2. Granting Secret Manager access to our custom service account...
gcloud secrets add-iam-policy-binding google-sheets-credentials ^
  --member="serviceAccount:rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com" ^
  --role="roles/secretmanager.secretAccessor"

echo.
echo 3. Verifying secret exists...
gcloud secrets versions list google-sheets-credentials

echo.
echo 4. Re-deploying the service...
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
  --set-env-vars="PRODUCT_MASTER_SPREADSHEET_ID=1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E" ^
  --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json" ^
  --set-secrets="/app/credentials.json=google-sheets-credentials:latest"

echo.
echo Deployment should complete successfully now!
pause
