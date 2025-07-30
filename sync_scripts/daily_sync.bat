@echo off
chcp 65001
echo ===================================================
echo 毎日の注文同期スクリプト
echo ===================================================

set BASE_URL=https://rakuten-order-sync-454314269549.asia-northeast1.run.app

:: まずスプレッドシートと同期
echo.
echo ステップ1: スプレッドシートと同期中...
curl -X POST "%BASE_URL%/sync-sheets"
echo.

:: 少し待機
timeout /t 3

:: 過去1日分の注文を同期
echo.
echo ステップ2: 過去1日分の注文を同期中...
curl "%BASE_URL%/sync-orders?days=1"

echo.
echo ===================================================
echo 本日の同期完了！
echo ===================================================
pause
