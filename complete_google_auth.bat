@echo off
echo === Google Sheets Authentication Setup ===
echo.

:: Check if credentials file already exists
if exist google-credentials.json (
    echo Found existing google-credentials.json
) else (
    echo Creating new credentials file...
    gcloud iam service-accounts keys create google-credentials.json ^
      --iam-account=rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com
)

echo.
echo === Step 1: Upload credentials to Secret Manager ===
gcloud secrets create google-sheets-credentials --data-file=google-credentials.json 2>nul
if %errorlevel% neq 0 (
    echo Secret already exists. Updating...
    gcloud secrets versions add google-sheets-credentials --data-file=google-credentials.json
)

echo.
echo === Step 2: Grant service account access to the secret ===
gcloud secrets add-iam-policy-binding google-sheets-credentials ^
  --member="serviceAccount:rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com" ^
  --role="roles/secretmanager.secretAccessor"

echo.
echo === Step 3: Update Cloud Run service with credentials ===
gcloud run services update rakuten-order-sync ^
  --region=asia-northeast1 ^
  --set-secrets="/app/credentials.json=google-sheets-credentials:latest" ^
  --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json"

echo.
echo === Step 4: Grant service account necessary permissions ===
gcloud projects add-iam-policy-binding sizuka-syouhin ^
  --member="serviceAccount:rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com" ^
  --role="roles/sheets.editor"

echo.
echo =============================================
echo Setup completed!
echo.
echo IMPORTANT: Now you need to share your Google Sheet with:
echo rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com
echo.
echo 1. Open your Google Sheet (ID: 1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E)
echo 2. Click "Share" button
echo 3. Add the email above with "Editor" permission
echo 4. Click "Send"
echo.
pause
