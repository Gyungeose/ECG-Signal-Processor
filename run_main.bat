@echo off
setlocal
set SCRIPT_DIR=%~dp0
set VENV=%SCRIPT_DIR%.venv\Scripts\python.exe
if exist "%VENV%" (
    "%VENV%" "%SCRIPT_DIR%main.py"
) else (
    echo Virtual environment not found at %VENV%
    echo Please run this project using the workspace venv Python.
    echo Example:
    echo   "%SCRIPT_DIR%\.venv\Scripts\python.exe" "%SCRIPT_DIR%main.py"
    pause
)
