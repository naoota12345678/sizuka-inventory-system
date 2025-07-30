@echo off
cd /d C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync

echo 仮想環境をアクティベート中...
call venv\Scripts\activate.bat

echo アプリケーションを起動中...
python main.py

pause
