@echo off
REM Network Scout - Windows Installation Script

echo ================================================
echo   Network Scout v2.2.9 - Installation
echo ================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Create virtual environment (optional but recommended)
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Warning: Could not create virtual environment
    echo Continuing with system Python...
) else (
    echo Virtual environment created successfully
    call venv\Scripts\activate.bat
)
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install dependencies
echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo ================================================
echo   Installation Complete!
echo ================================================
echo.
echo To run Network Scout:
if exist venv (
    echo   1. Activate virtual environment: venv\Scripts\activate.bat
    echo   2. Run: python network_suite.py
) else (
    echo   python network_suite.py
)
echo.
echo Or simply double-click run_wifi_scout.bat
echo.
pause
