@echo off
REM SpendAlizer Stop Script for Windows

echo Stopping SpendAlizer...
echo.

REM Stop Backend (port 8001)
echo Stopping backend server (port 8001)...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8001" ^| find "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   Backend stopped
)
echo.

REM Stop Frontend (port 3000)
echo Stopping frontend server (port 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
    echo   Frontend stopped
)
echo.

echo All servers stopped
echo.
pause
