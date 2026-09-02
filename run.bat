@echo off
title Laptop Info Collector
cd /d "%~dp0"

echo ============================================================
echo   Laptop Info Collector
echo ============================================================
echo.

REM Try py first, then python
where py >nul 2>nul
if %errorlevel%==0 (
    echo Using: py
    echo.
    py laptop_info.py
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        echo Using: python
        echo.
        python laptop_info.py
    ) else (
        echo [ERROR] Python not found.
        echo Please install Python 3.8+ from https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo   Done! Result saved as laptop_info_*.json
echo   Open it with Notepad or VSCode to view hardware info.
echo ============================================================
echo.
pause
