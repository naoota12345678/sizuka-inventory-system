@echo off
echo デスクトップにショートカットを作成します...

set TARGET_PATH=C:\Users\naoot\Desktop\ｐ\sizukatest\rakuten-order-sync\sync_scripts\sync_from_feb11.bat
set SHORTCUT_PATH=C:\Users\naoot\Desktop\2月11日から同期.lnk

powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%TARGET_PATH%'; $Shortcut.IconLocation = 'shell32.dll,21'; $Shortcut.Save()"

echo ショートカットを作成しました！
echo デスクトップの「2月11日から同期」をダブルクリックで実行できます。
pause
