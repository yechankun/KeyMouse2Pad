@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv-win\Scripts\python.exe" (
    py -3 -m venv .venv-win
)

set NEED_INSTALL=0

".venv-win\Scripts\python.exe" -m pip show pyinstaller >nul 2>nul
if errorlevel 1 set NEED_INSTALL=1

if "%NEED_INSTALL%"=="1" (
    ".venv-win\Scripts\python.exe" -m pip install pyinstaller
)

".venv-win\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --paths vendor ^
    --hidden-import vgamepad ^
    --hidden-import vgamepad.win.vigem_client ^
    --hidden-import vgamepad.win.vigem_commons ^
    --hidden-import vgamepad.win.virtual_gamepad ^
    --add-binary "vendor\vgamepad\win\vigem\client\x64\ViGEmClient.dll;vgamepad\win\vigem\client\x64" ^
    --add-binary "vendor\vgamepad\win\vigem\client\x86\ViGEmClient.dll;vgamepad\win\vigem\client\x86" ^
    --name KeyMouse2Pad ^
    gui\converter_gui.py

echo.
echo Built: dist\KeyMouse2Pad.exe
