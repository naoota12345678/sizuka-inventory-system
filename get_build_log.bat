@echo off
echo Cloud Buildの最新ログを取得します...

cd /d "C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync"

REM 最新のビルドIDを取得
for /f "tokens=1" %%i in ('gcloud builds list --limit=1 --format="value(id)"') do set BUILD_ID=%%i

echo ビルドID: %BUILD_ID%
echo.

REM ビルドログを取得してファイルに保存
gcloud builds log %BUILD_ID% > latest_build.log 2>&1

REM requirements.txt関連の行を抽出
echo === Requirements関連 ===
findstr /i "requirements google-api-python-client" latest_build.log

echo.
echo === Dockerfileのステップ ===
findstr /i "step dockerfile copy" latest_build.log

echo.
echo 完全なログは latest_build.log に保存されました
pause