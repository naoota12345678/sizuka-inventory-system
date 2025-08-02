@echo off
echo === Simple Cloud Run Deploy ===
echo.

REM Cloud Buildを使用してデプロイ
echo Building and deploying to Cloud Run...
gcloud builds submit --config cloudbuild.yaml .

echo.
echo === Deployment Complete ===
echo Service URL: https://sizuka-inventory-system-1025485420770.asia-northeast1.run.app
pause