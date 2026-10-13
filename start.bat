@echo off
title PDF Unlocker Pro
echo ======================================================
echo           Starting PDF Unlocker Web App
echo ======================================================
echo.
cd /d "%~dp0"

echo [1/2] Checking Python packages...
python -m pip install -r requirements.txt >nul 2>&1

echo [2/2] Starting Web Server...
echo Open your browser at: http://localhost:5000
echo.
start http://localhost:5000
python app.py
pause
