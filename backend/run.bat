@echo off
echo ================================================
echo   🦐 Starting Shrimp Detection Server
echo ================================================
echo.

REM Check if .env exists
if not exist .env (
    echo ❌ .env file not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Check if MongoDB is running
net start | find "MongoDB" >nul
if errorlevel 1 (
    echo ⚠️  MongoDB not running. Attempting to start...
    net start MongoDB >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  Could not start MongoDB
        echo You can continue if using MongoDB Atlas
        echo.
    )
)

echo Starting Flask server...
echo Server will run at: http://localhost:8000
echo.
echo To access from internet, run ngrok in another terminal:
echo   ngrok http 8000
echo.
echo Press Ctrl+C to stop the server
echo.
echo ================================================
echo.

python app.py

pause

