@echo off
cd /d "%~dp0"
echo Starting Push Assistant...
echo (Close this window to stop. Or use the tray icon -> Quit)
echo.
python run.py
pause
