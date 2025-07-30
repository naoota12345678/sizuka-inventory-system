@echo off
cd /d C:\Users\naoot\Desktop\p\sizukatest\rakuten-order-sync

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting application...
python main.py

pause
