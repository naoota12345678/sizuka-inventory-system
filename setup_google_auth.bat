@echo off
echo Creating service account for Google Sheets access...

:: Create service account
gcloud iam service-accounts create rakuten-order-sync-sa ^
  --display-name="Rakuten Order Sync Service Account"

:: Get service account email
for /f "tokens=*" %%i in ('gcloud projects describe sizuka-syouhin --format="value(projectNumber)"') do set PROJECT_NUMBER=%%i
set SA_EMAIL=rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com

:: Grant necessary permissions
echo Granting permissions...
gcloud projects add-iam-policy-binding sizuka-syouhin ^
  --member="serviceAccount:%SA_EMAIL%" ^
  --role="roles/sheets.editor"

:: Create key file
echo Creating credentials file...
gcloud iam service-accounts keys create google-credentials.json ^
  --iam-account=%SA_EMAIL%

echo.
echo Service account created!
echo.
echo IMPORTANT: 
echo 1. Share your Google Sheet with this email: %SA_EMAIL%
echo 2. Upload the google-credentials.json file to Cloud Run as a secret
echo.
pause
