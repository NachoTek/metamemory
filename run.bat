@echo off
REM Launch metamemory application with proper Python path setup

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Add src directory to Python path so metamemory module can be found
set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"

REM Launch the application
echo Starting metamemory...
cd /d "%SCRIPT_DIR%"
python -m metamemory.main

REM Pause if there was an error
if errorlevel 1 (
    echo.
    echo Application exited with error code %errorlevel%
    pause
)
