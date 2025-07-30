@echo off
chcp 65001
echo ===================================================
echo 2月11日以降の注文データを同期します
echo ===================================================

set BASE_URL=https://rakuten-order-sync-454314269549.asia-northeast1.run.app

:: まずスプレッドシートと同期
echo.
echo ステップ1: スプレッドシートと同期中...
curl -X POST "%BASE_URL%/sync-sheets"
echo.

:: 少し待機
timeout /t 5

:: 2月11日から今日までの注文を同期
echo.
echo ステップ2: 2月11日から今日までの注文を同期中...
:: 日付形式: YYYY-MM-DD
curl "%BASE_URL%/sync-orders-range?start_date=2025-02-11&end_date=2025-06-09"

echo.
echo ===================================================
echo 同期完了！
echo ===================================================
pause
