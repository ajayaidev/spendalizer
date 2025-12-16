"""Authentication helpers and dependencies."""
import bcrypt
import jwt
import secrets
import logging
import aiosmtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL

# Security
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_token(user_id: str) -> str:
    """Create a JWT token for a user."""
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    return jwt.encode({"user_id": user_id, "exp": expiration}, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency to get the current user from JWT token."""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["user_id"]
    except:
        raise HTTPException(status_code=401, detail="Invalid authentication")


def generate_reset_token() -> str:
    """Generate secure random token for password reset."""
    return secrets.token_urlsafe(32)


async def send_email(to_email: str, subject: str, body: str):
    """Send email using SMTP."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logging.warning("Email not configured. Skipping email send.")
        return False
    
    try:
        logging.info(f"Attempting to send email using {SMTP_HOST}:{SMTP_PORT}")
        message = MIMEMultipart()
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
        )
        logging.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False
