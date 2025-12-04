@echo off
REM SpendAlizer Start Script for Windows

echo Starting SpendAlizer...
echo.

cd /d "%~dp0"

REM Create logs directory
if not exist "logs" mkdir logs

REM Check MongoDB
echo Checking MongoDB...
mongosh --eval "db.version()" >nul 2>&1
if errorlevel 1 (
    echo   ERROR: MongoDB is not running
    echo   Please start MongoDB service from Services app
    echo.
    pause
    exit /b 1
)
echo   MongoDB is running
echo.

REM Start Backend
echo Starting backend server...
cd backend

if not exist "venv" (
    echo   Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

if not exist "venv\.installed" (
    echo   Installing dependencies...
    pip install -r requirements.txt --quiet
    type nul > venv\.installed
)

start /B uvicorn server:app --host 0.0.0.0 --port 8001 --reload > ..\logs\backend.log 2>&1
echo   Backend started on http://localhost:8001
cd ..
timeout /t 3 /nobreak >nul

REM Start Frontend
echo Starting frontend server...
cd frontend

if not exist "node_modules" (
    echo   Installing dependencies...
    if exist "yarn.lock" (
        yarn install --silent
    ) else (
        npm install --legacy-peer-deps --silent
    )
)

if exist "yarn.lock" (
    start /B yarn start > ..\logs\frontend.log 2>&1
) else (
    start /B npm start > ..\logs\frontend.log 2>&1
)
echo   Frontend starting on http://localhost:3000
cd ..

echo.
echo ========================================
echo   SpendAlizer is running!
echo ========================================
echo.
echo Access:
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8001
echo   API Docs: http://localhost:8001/docs
echo.
echo Stop servers: stop.bat
echo.
pause
