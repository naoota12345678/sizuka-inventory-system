@echo off
echo Starting deployment of Rakuten Order Sync API...

:: Move to project directory
cd /d "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"

:: Set project
echo Setting up project...
gcloud config set project sizuka-syouhin

:: Deploy
echo Building and deploying application...
gcloud builds submit --config=cloudbuild.yaml

echo.
echo Deployment command executed.
echo.
echo To check build status, run:
echo gcloud builds list --limit=1
echo.
pause