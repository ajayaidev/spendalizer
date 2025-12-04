#!/bin/bash

# SpendAlizer Status Script
# Check status of backend and frontend servers

echo "📊 SpendAlizer Status"
echo "====================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to check if a process is running on a port
check_port() {
    lsof -ti:$1 > /dev/null 2>&1
}

# Check MongoDB
echo "🗄️  MongoDB:"
if mongosh --eval "db.version()" > /dev/null 2>&1; then
    VERSION=$(mongosh --quiet --eval "db.version()")
    echo -e "   ${GREEN}✓ Running (v$VERSION)${NC}"
else
    echo -e "   ${RED}✗ Not running${NC}"
    echo "   Start: brew services start mongodb-community"
fi
echo ""

# Check Backend
echo "🔧 Backend Server (Port 8001):"
if check_port 8001; then
    PID=$(lsof -ti:8001)
    echo -e "   ${GREEN}✓ Running (PID: $PID)${NC}"
    echo "   URL: http://localhost:8001"
    echo "   API Docs: http://localhost:8001/docs"
else
    echo -e "   ${RED}✗ Not running${NC}"
fi
echo ""

# Check Frontend
echo "⚛️  Frontend Server (Port 3000):"
if check_port 3000; then
    PID=$(lsof -ti:3000)
    echo -e "   ${GREEN}✓ Running (PID: $PID)${NC}"
    echo "   URL: http://localhost:3000"
else
    echo -e "   ${RED}✗ Not running${NC}"
fi
echo ""

# Check Git Status
echo "📦 Git Repository:"
cd "$(dirname "$0")"
BRANCH=$(git branch --show-current)
BEHIND=$(git rev-list HEAD..origin/main --count 2>/dev/null || echo "?")
UNCOMMITTED=$(git status --porcelain | wc -l | tr -d ' ')

echo "   Branch: $BRANCH"
if [ "$BEHIND" = "?" ]; then
    echo -e "   ${YELLOW}⚠ Unable to check remote status${NC}"
elif [ "$BEHIND" -eq 0 ]; then
    echo -e "   ${GREEN}✓ Up to date with remote${NC}"
else
    echo -e "   ${YELLOW}⚠ Behind by $BEHIND commit(s)${NC}"
    echo "   Run: ./update.sh"
fi

if [ "$UNCOMMITTED" -gt 0 ]; then
    echo -e "   ${YELLOW}⚠ $UNCOMMITTED uncommitted change(s)${NC}"
fi
echo ""

# Quick Actions
echo "🎯 Quick Actions:"
if ! check_port 8001 || ! check_port 3000; then
    echo "   Start servers:  ./start.sh"
fi
if check_port 8001 || check_port 3000; then
    echo "   Stop servers:   ./stop.sh"
    echo "   Restart:        ./stop.sh && ./start.sh"
fi
if [ "$BEHIND" != "0" ] && [ "$BEHIND" != "?" ]; then
    echo "   Update & Restart: ./update.sh"
fi
echo "   View backend logs:  tail -f logs/backend.log"
echo "   View frontend logs: tail -f logs/frontend.log"
echo ""
