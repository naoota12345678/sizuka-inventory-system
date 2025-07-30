@echo off
echo === Checking Google Sheets Setup Status ===
echo.

echo 1. Listing existing secrets...
gcloud secrets list
echo.

echo 2. Checking if google-sheets-credentials exists...
gcloud secrets describe google-sheets-credentials 2>nul
if %errorlevel% neq 0 (
    echo Secret does not exist. Creating it now...
    gcloud secrets create google-sheets-credentials --data-file=google-credentials.json
) else (
    echo Secret exists. Adding new version...
    gcloud secrets versions add google-sheets-credentials --data-file=google-credentials.json
)

echo.
echo 3. Setting permissions...
gcloud secrets add-iam-policy-binding google-sheets-credentials ^
  --member="serviceAccount:454314269549-compute@developer.gserviceaccount.com" ^
  --role="roles/secretmanager.secretAccessor"

echo.
echo 4. Testing with environment variable approach instead...
echo Reading credentials file content...
type google-credentials.json > temp_creds.txt

echo.
echo 5. Alternative approach - using environment variable...
set /p CREDS_CONTENT=<google-credentials.json

echo.
pause
