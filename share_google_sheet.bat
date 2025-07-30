@echo off
echo === Checking Google Sheets Access ===
echo.

echo Service account email:
echo rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com
echo.

echo Opening Google Sheet in browser...
start https://docs.google.com/spreadsheets/d/1mLg1N0a1wubEIdKSouiW_jDaWUnuFLBxj8greczuS3E/edit#gid=0

echo.
echo Please ensure:
echo 1. Click the "Share" button in the top right
echo 2. Add: rakuten-order-sync-sa@sizuka-syouhin.iam.gserviceaccount.com
echo 3. Set permission to "Editor"
echo 4. Uncheck "Notify people"
echo 5. Click "Share"
echo.
pause
