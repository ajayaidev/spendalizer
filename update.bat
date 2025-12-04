@echo off
REM SpendAlizer Update Script for Windows

echo ========================================
echo   SpendAlizer Update Script
echo ========================================
echo.

cd /d "%~dp0"

REM Step 1: Stop Backend
echo [1/6] Stopping backend server...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8001" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul
echo   Backend stopped
echo.

REM Step 2: Stop Frontend
echo [2/6] Stopping frontend server...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul
echo   Frontend stopped
echo.

REM Step 3: Pull from Git
echo [3/6] Pulling latest changes from GitHub...
git pull origin main
echo   Code updated
echo.

REM Step 4: Update Backend Dependencies
echo [4/6] Updating backend dependencies...
cd backend

if not exist "venv" (
    echo   Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
echo   Backend dependencies updated
cd ..
echo.

REM Step 5: Update Frontend Dependencies
echo [5/6] Updating frontend dependencies...
cd frontend

if exist "yarn.lock" (
    yarn install --silent
) else (
    npm install --legacy-peer-deps --silent
)
echo   Frontend dependencies updated
cd ..
echo.

REM Step 6: Start Servers
echo [6/6] Starting servers...
echo.

REM Create logs directory
if not exist "logs" mkdir logs

REM Start Backend
echo   Starting backend...
cd backend
call venv\Scripts\activate.bat
start /B uvicorn server:app --host 0.0.0.0 --port 8001 --reload > ..\logs\backend.log 2>&1
cd ..
timeout /t 3 /nobreak >nul

REM Start Frontend
echo   Starting frontend...
cd frontend
if exist "yarn.lock" (
    start /B yarn start > ..\logs\frontend.log 2>&1
) else (
    start /B npm start > ..\logs\frontend.log 2>&1
)
cd ..

echo.
echo ========================================
echo   Update complete!
echo ========================================
echo.
echo Server Status:
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:3000
echo.
echo Logs:
echo   Backend:  logs\backend.log
echo   Frontend: logs\frontend.log
echo.
echo To stop servers: stop.bat
echo.
pause
