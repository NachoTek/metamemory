@echo off
REM Launch metamemory (meetandread) application
REM No codebase changes needed — just sets PYTHONPATH and runs.

set "SCRIPT_DIR=%~dp0"
set "PYTHONPATH=%SCRIPT_DIR%src"
cd /d "%SCRIPT_DIR%"

echo Starting metamemory...
python -m metamemory.main

if errorlevel 1 (
    echo.
    echo Application exited with error code %errorlevel%
    pause
)
