"""Application configuration and environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7

# Email configuration
SMTP_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('EMAIL_PORT', '587'))
SMTP_USER = os.environ.get('EMAIL_USER', '')
SMTP_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
FROM_EMAIL = os.environ.get('EMAIL_FROM', SMTP_USER)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Ollama configuration
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3')
