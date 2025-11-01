@echo off
echo ================================================
echo   🦐 Shrimp Detection Backend Setup
echo ================================================
echo.

REM Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python found

REM Check pip
echo.
echo [2/5] Checking pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip not found!
    pause
    exit /b 1
)
echo ✅ pip found

REM Install dependencies
echo.
echo [3/5] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed

REM Check .env
echo.
echo [4/5] Checking .env file...
if not exist .env (
    echo ⚠️  .env file not found. Creating from template...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Please edit .env file and add your credentials:
    echo    - Cloudinary credentials
    echo    - MongoDB URI
    echo    - YOLO model path
    echo.
    notepad .env
) else (
    echo ✅ .env file exists
)

REM Check MongoDB
echo.
echo [5/5] Checking MongoDB...
net start | find "MongoDB" >nul
if errorlevel 1 (
    echo ⚠️  MongoDB service not running
    echo    Attempting to start...
    net start MongoDB >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  Could not start MongoDB automatically
        echo    Please start MongoDB manually or use MongoDB Atlas
    ) else (
        echo ✅ MongoDB started
    )
) else (
    echo ✅ MongoDB is running
)

echo.
echo ================================================
echo   Setup Complete!
echo ================================================
echo.
echo Next steps:
echo 1. Make sure .env is configured correctly
echo 2. Place your YOLO model in models/ folder
echo 3. Run: python app.py
echo.
pause

