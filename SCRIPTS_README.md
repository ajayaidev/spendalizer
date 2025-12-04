# SpendAlizer Management Scripts

Easy-to-use scripts for managing SpendAlizer servers and updates.

## 📁 Available Scripts

### For macOS/Linux:
- **`update.sh`** - Stop servers, pull updates, install dependencies, restart
- **`start.sh`** - Start backend and frontend servers
- **`stop.sh`** - Stop all servers
- **`status.sh`** - Check server and git status

### For Windows:
- **`update.bat`** - Stop servers, pull updates, install dependencies, restart
- **`start.bat`** - Start backend and frontend servers
- **`stop.bat`** - Stop all servers

---

## 🚀 Quick Start

### First Time Setup (macOS/Linux)

```bash
# Make scripts executable
chmod +x *.sh

# Start servers
./start.sh
```

### First Time Setup (Windows)

```cmd
REM Just double-click start.bat
REM Or run from command prompt:
start.bat
```

---

## 📋 Script Details

### 1. Update Script (`update.sh` / `update.bat`)

**Automatically handles complete update workflow:**

```bash
./update.sh  # macOS/Linux
update.bat   # Windows
```

**What it does:**
1. ✅ Stops backend server (port 8001)
2. ✅ Stops frontend server (port 3000)
3. ✅ Pulls latest changes from GitHub
4. ✅ Updates backend dependencies (if requirements.txt changed)
5. ✅ Updates frontend dependencies (if package.json changed)
6. ✅ Restarts both servers in background

**When to use:**
- After pulling updates from GitHub
- When dependencies are updated
- For quick restart with latest code

**Output:**
- Logs written to `logs/backend.log` and `logs/frontend.log`
- Shows server URLs and PIDs

---

### 2. Start Script (`start.sh` / `start.bat`)

**Start servers from scratch:**

```bash
./start.sh  # macOS/Linux
start.bat   # Windows
```

**What it does:**
1. ✅ Checks if MongoDB is running
2. ✅ Creates virtual environment (if needed)
3. ✅ Installs backend dependencies (if needed)
4. ✅ Starts backend server on port 8001
5. ✅ Installs frontend dependencies (if needed)
6. ✅ Starts frontend server on port 3000

**When to use:**
- First time starting the app
- After a fresh git clone
- When servers are stopped

---

### 3. Stop Script (`stop.sh` / `stop.bat`)

**Stop all servers:**

```bash
./stop.sh  # macOS/Linux
stop.bat   # Windows
```

**What it does:**
1. ✅ Kills backend process on port 8001
2. ✅ Kills frontend process on port 3000

**When to use:**
- Before pulling updates manually
- To free up ports
- Before system shutdown

---

### 4. Status Script (`status.sh` - macOS/Linux only)

**Check system status:**

```bash
./status.sh
```

**What it shows:**
- ✅ MongoDB status and version
- ✅ Backend server status (running/stopped)
- ✅ Frontend server status (running/stopped)
- ✅ Git repository status
- ✅ Commits behind remote
- ✅ Uncommitted changes
- ✅ Quick action suggestions

**When to use:**
- To check if servers are running
- To see if updates are available
- To get server URLs

---

## 📝 Log Files

All logs are stored in the `logs/` directory:

```bash
# View backend logs (macOS/Linux)
tail -f logs/backend.log

# View frontend logs (macOS/Linux)
tail -f logs/frontend.log

# View logs (Windows)
type logs\backend.log
type logs\frontend.log
```

---

## 🔄 Common Workflows

### Daily Development

```bash
# Morning: Start servers
./start.sh

# Evening: Stop servers
./stop.sh
```

### Pull Updates from GitHub

```bash
# Option 1: Use update script (recommended)
./update.sh

# Option 2: Manual
./stop.sh
git pull origin main
cd backend && pip install -r requirements.txt && cd ..
cd frontend && yarn install && cd ..
./start.sh
```

### Check if Update Available

```bash
./status.sh  # macOS/Linux only
```

### Restart Servers

```bash
# Quick restart
./stop.sh && ./start.sh

# Or use update script (pulls latest + restarts)
./update.sh
```

---

## ⚙️ Configuration

### Change Ports

Edit the scripts if you need different ports:

**Backend (default: 8001):**
- In `start.sh`: Change `--port 8001`
- In `update.sh`: Change `--port 8001`

**Frontend (default: 3000):**
- Automatically uses port 3000 (React default)
- Set `PORT=3001` environment variable to change

### Background vs Foreground

**Current setup:** Servers run in background with logs

**To run in foreground** (see output directly):

Edit `start.sh` and remove `nohup` and `&`:

```bash
# Change from:
nohup uvicorn server:app --host 0.0.0.0 --port 8001 --reload > ../logs/backend.log 2>&1 &

# To:
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

## 🐛 Troubleshooting

### "Permission denied" on macOS/Linux

```bash
chmod +x *.sh
```

### "Port already in use"

```bash
./stop.sh
# Or manually:
lsof -ti:8001 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### "MongoDB not running"

```bash
# macOS
brew services start mongodb-community

# Linux
sudo systemctl start mongodb

# Windows
# Start MongoDB service from Services app
```

### Scripts not working after update

```bash
# Re-download scripts
git pull origin main

# Make executable (macOS/Linux)
chmod +x *.sh
```

### Backend fails to start

```bash
# Check logs
tail -f logs/backend.log

# Common fixes:
cd backend
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Frontend fails to start

```bash
# Check logs
tail -f logs/frontend.log

# Common fixes:
cd frontend
rm -rf node_modules yarn.lock
yarn install
```

---

## 📦 Directory Structure

```
spendalizer/
├── update.sh          # Update script (macOS/Linux)
├── start.sh           # Start script (macOS/Linux)
├── stop.sh            # Stop script (macOS/Linux)
├── status.sh          # Status script (macOS/Linux)
├── update.bat         # Update script (Windows)
├── start.bat          # Start script (Windows)
├── stop.bat           # Stop script (Windows)
├── logs/              # Log files (auto-created)
│   ├── backend.log
│   └── frontend.log
├── backend/           # Backend code
├── frontend/          # Frontend code
└── README.md          # Main documentation
```

---

## 🎯 Best Practices

1. **Always use `update.sh`** when pulling updates from GitHub
2. **Check `status.sh`** before starting work
3. **Stop servers** before shutting down your computer
4. **Monitor logs** if something goes wrong
5. **Keep scripts updated** with `git pull`

---

## 🆘 Need Help?

If scripts aren't working:

1. Check the logs: `tail -f logs/backend.log`
2. Verify MongoDB is running: `mongosh --eval "db.version()"`
3. Check ports are free: `lsof -i :8001` and `lsof -i :3000`
4. Try manual start to see errors directly

---

**Happy coding! 🚀**
