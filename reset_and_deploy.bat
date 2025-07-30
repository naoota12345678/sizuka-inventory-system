@echo off
echo === Complete Service Reset ===
echo.

echo 1. Deleting existing Cloud Run service...
gcloud run services delete rakuten-order-sync --region=asia-northeast1 --quiet

echo.
echo 2. Waiting for deletion to complete...
timeout /t 10

echo.
echo 3. Deploying fresh service with embedded credentials...
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
  --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json"

echo.
echo 4. Testing the fresh deployment...
timeout /t 10
curl -X GET "https://rakuten-order-sync-454314269549.asia-northeast1.run.app/health"
echo.
echo.

echo 5. Testing Google Sheets sync...
curl -X POST "https://rakuten-order-sync-454314269549.asia-northeast1.run.app/sync-product-master" ^
  -H "Content-Type: application/json" ^
  -H "Content-Length: 0"
echo.
echo.

echo Deployment completed!
pause
