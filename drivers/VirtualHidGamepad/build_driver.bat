@echo off
setlocal
cd /d "%~dp0"

where msbuild >nul 2>nul
if errorlevel 1 (
    echo MSBuild was not found in PATH.
    echo Open "x64 Native Tools Command Prompt for VS" with Windows WDK installed, then run this script.
    exit /b 1
)

msbuild VirtualHidGamepad.vcxproj /p:Configuration=Release /p:Platform=x64

