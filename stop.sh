#!/bin/bash

# SpendAlizer Stop Script
# Stops backend and frontend servers

echo "🛑 Stopping SpendAlizer..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Function to check if a process is running on a port
check_port() {
    lsof -ti:$1 > /dev/null 2>&1
}

# Stop Backend
echo "🔧 Stopping backend server (port 8001)..."
if check_port 8001; then
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
    sleep 1
    echo -e "   ${GREEN}✓ Backend stopped${NC}"
else
    echo "   Backend not running"
fi
echo ""

# Stop Frontend
echo "⚛️  Stopping frontend server (port 3000)..."
if check_port 3000; then
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 1
    echo -e "   ${GREEN}✓ Frontend stopped${NC}"
else
    echo "   Frontend not running"
fi
echo ""

echo -e "${GREEN}✅ All servers stopped${NC}"
echo ""
