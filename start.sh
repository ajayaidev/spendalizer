#!/bin/bash

# SpendAlizer Start Script
# Starts backend and frontend servers

set -e

echo "🚀 Starting SpendAlizer..."
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if MongoDB is running
echo "🔍 Checking MongoDB..."
if mongosh --eval "db.version()" > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ MongoDB is running${NC}"
else
    echo -e "   ${RED}✗ MongoDB is not running${NC}"
    echo "   Please start MongoDB first:"
    echo "   macOS:  brew services start mongodb-community"
    echo "   Linux:  sudo systemctl start mongodb"
    exit 1
fi
echo ""

# Start Backend
echo "🔧 Starting backend server..."
cd backend

if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "   Installing dependencies..."
    pip install -r requirements.txt --quiet
    touch venv/.installed
fi

nohup uvicorn server:app --host 0.0.0.0 --port 8001 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "   ${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo "   Running on: http://localhost:8001"
cd ..
echo ""

# Wait for backend to start
sleep 3

# Start Frontend
echo "⚛️  Starting frontend server..."
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    if command -v yarn &> /dev/null; then
        yarn install --silent
    else
        npm install --legacy-peer-deps --silent
    fi
fi

if command -v yarn &> /dev/null; then
    nohup yarn start > ../logs/frontend.log 2>&1 &
else
    nohup npm start > ../logs/frontend.log 2>&1 &
fi
FRONTEND_PID=$!
echo -e "   ${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo "   Opening on: http://localhost:3000"
cd ..
echo ""

echo -e "${GREEN}✅ SpendAlizer is running!${NC}"
echo ""
echo "📊 Access:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8001"
echo "   API Docs: http://localhost:8001/docs"
echo ""
echo "📝 View logs:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo ""
echo "🛑 Stop servers: ./stop.sh"
echo ""
