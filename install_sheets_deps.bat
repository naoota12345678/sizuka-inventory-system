@echo off
REM Google Sheets API関連のライブラリをインストール

echo Google Sheets API用ライブラリをインストールしています...

pip install google-api-python-client==2.95.0
pip install google-auth-httplib2==0.1.0
pip install google-auth-oauthlib==1.0.0
pip install pandas==2.0.3

echo インストール完了！
pause
