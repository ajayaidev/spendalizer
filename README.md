# SpendAlizer - Personal Finance Management SaaS

![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![React](https://img.shields.io/badge/react-19.0-61dafb.svg)

**SpendAlizer** is a privacy-first personal finance management application that helps you track, categorize, and analyze your financial transactions with AI-powered insights.

## ✨ Features

- 🔐 **Privacy-First** - Manual CSV/XLSX imports, no bank API integrations
- 🤖 **AI Categorization** - Local Ollama LLM integration
- 📊 **Analytics** - Visual charts and spending insights
- 🏦 **Multi-Account** - Banks & credit cards
- ⚡ **Rules Engine** - Pattern-based auto-categorization
- 💾 **Local Data** - MongoDB on your server

## 🚀 Quick Start

### Prerequisites
- Node.js v18+
- Python 3.9+
- MongoDB v5.0+
- Ollama (optional)

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd spendalizer

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend setup (new terminal)
cd frontend
yarn install
yarn start
```

Open http://localhost:3000

## 📋 Configuration

**Backend** (`backend/.env`):
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="spendalizer"
JWT_SECRET="your-secret-key"
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3"
```

**Frontend** (`frontend/.env`):
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## 🏗️ Tech Stack

**Backend:** FastAPI, MongoDB, Motor, Pandas, Ollama, JWT
**Frontend:** React 19, Shadcn/UI, Tailwind CSS, Recharts
**Design:** Manrope & IBM Plex Sans fonts

## 📊 Supported Banks

- HDFC Bank, SBI Bank, Federal Bank
- HDFC CC, SBI CC, Standard Chartered CC

## 🎯 Usage

1. Register/Login
2. Add accounts (bank/credit card)
3. Import CSV statements
4. Create categorization rules
5. View analytics

## 📄 License

MIT License

---

Built with ❤️ for privacy-conscious finance tracking
