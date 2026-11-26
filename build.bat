@echo off
REM Builds dist\Nazar\Nazar.exe  (double-click this file, or run it from cmd)
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller || goto :error
python -m PyInstaller --noconfirm --clean --windowed --name Nazar ^
  --icon assets\nazar.ico ^
  --add-data "assets;assets" ^
  --collect-all mediapipe ^
  run_nazar.py || goto :error
echo.
echo Done! Your app is in: %cd%\dist\Nazar\Nazar.exe
explorer dist\Nazar
pause
exit /b 0
:error
echo.
echo Build failed. Scroll up to see the error.
pause
exit /b 1
