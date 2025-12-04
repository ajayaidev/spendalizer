#!/bin/bash

# SpendAlizer Update Script
# This script stops servers, pulls updates, installs dependencies, and restarts

set -e  # Exit on error

echo "🚀 SpendAlizer Update Script"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📂 Working directory: $SCRIPT_DIR"
echo ""

# Function to check if a process is running on a port
check_port() {
    lsof -ti:$1 > /dev/null 2>&1
}

# Step 1: Stop Backend
echo "🛑 Step 1/6: Stopping backend server..."
if check_port 8001; then
    echo "   Killing process on port 8001..."
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
    sleep 2
    echo -e "   ${GREEN}✓ Backend stopped${NC}"
else
    echo "   Backend not running"
fi
echo ""

# Step 2: Stop Frontend
echo "🛑 Step 2/6: Stopping frontend server..."
if check_port 3000; then
    echo "   Killing process on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
    echo -e "   ${GREEN}✓ Frontend stopped${NC}"
else
    echo "   Frontend not running"
fi
echo ""

# Step 3: Pull from Git
echo "📥 Step 3/6: Pulling latest changes from GitHub..."
git fetch origin
BEHIND=$(git rev-list HEAD..origin/main --count)

if [ "$BEHIND" -eq 0 ]; then
    echo -e "   ${GREEN}✓ Already up to date${NC}"
else
    echo "   Found $BEHIND new commit(s)"
    git pull origin main
    echo -e "   ${GREEN}✓ Code updated${NC}"
fi
echo ""

# Step 4: Update Backend Dependencies
echo "📦 Step 4/6: Updating backend dependencies..."
cd backend

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Check if requirements changed
if git diff HEAD@{1} HEAD -- requirements.txt > /dev/null 2>&1; then
    echo "   requirements.txt changed, updating packages..."
    pip install -r requirements.txt --quiet
    echo -e "   ${GREEN}✓ Backend dependencies updated${NC}"
else
    echo "   No changes in requirements.txt"
fi

cd ..
echo ""

# Step 5: Update Frontend Dependencies
echo "📦 Step 5/6: Updating frontend dependencies..."
cd frontend

# Check if package.json changed
if git diff HEAD@{1} HEAD -- package.json > /dev/null 2>&1; then
    echo "   package.json changed, updating packages..."
    if command -v yarn &> /dev/null; then
        yarn install --silent
    else
        npm install --legacy-peer-deps --silent
    fi
    echo -e "   ${GREEN}✓ Frontend dependencies updated${NC}"
else
    echo "   No changes in package.json"
fi

cd ..
echo ""

# Step 6: Start Servers
echo "🚀 Step 6/6: Starting servers..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Backend in background
echo "   Starting backend..."
cd backend
source venv/bin/activate
nohup uvicorn server:app --host 0.0.0.0 --port 8001 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
cd ..

# Wait a moment for backend to start
sleep 3

# Start Frontend in background
echo "   Starting frontend..."
cd frontend
if command -v yarn &> /dev/null; then
    nohup yarn start > ../logs/frontend.log 2>&1 &
else
    nohup npm start > ../logs/frontend.log 2>&1 &
fi
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"
cd ..

echo ""
echo -e "${GREEN}✅ Update complete!${NC}"
echo ""
echo "📊 Server Status:"
echo "   Backend:  http://localhost:8001"
echo "   Frontend: http://localhost:3000"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "🛑 To stop servers: ./stop.sh"
echo ""
