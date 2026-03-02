@echo off
REM Network Scout - Quick Launch Script

echo Starting Network Scout v2.2.9...
echo.

REM Check if virtual environment exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run the application
python network_suite.py

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
