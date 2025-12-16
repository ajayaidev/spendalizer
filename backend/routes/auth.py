"""Authentication routes."""
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends

from database import db
from auth import hash_password, verify_password, create_token, get_current_user, generate_reset_token, send_email
from config import FRONTEND_URL
from models.schemas import User, UserRegister, UserLogin, ForgotPasswordRequest, ResetPasswordRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(user_data: UserRegister):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password)
    )
    
    doc = {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'password_hash': user.password_hash,
        'created_at': user.created_at.isoformat()
    }
    await db.users.insert_one(doc)
    
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}


@router.post("/login")
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc or not verify_password(credentials.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user_doc["id"])
    return {"token": token, "user": {"id": user_doc["id"], "email": user_doc["email"], "name": user_doc["name"]}}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, req: Request):
    user_doc = await db.users.find_one({"email": request.email})
    
    if not user_doc:
        logging.info(f"Password reset requested for non-existent email: {request.email}")
        return {"message": "If the email exists, a reset link has been sent"}
    
    reset_token = generate_reset_token()
    expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    
    await db.users.update_one(
        {"id": user_doc["id"]},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expiration": expiration.isoformat()
        }}
    )
    
    origin = req.headers.get("origin") or req.headers.get("referer", "").rstrip("/")
    frontend_url = origin if origin and origin.startswith("http") else FRONTEND_URL
    
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    email_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Reset Your SpendAlizer Password</h2>
            <p>Hi {user_doc['name']},</p>
            <p>You requested to reset your password. Click the button below to reset it:</p>
            <p style="margin: 30px 0;">
                <a href="{reset_link}" 
                   style="background-color: #4169E1; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 6px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="color: #666; word-break: break-all;">{reset_link}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #999; font-size: 12px;">SpendAlizer - Personal Finance Management</p>
        </body>
    </html>
    """
    
    await send_email(request.email, "Reset Your Password - SpendAlizer", email_body)
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    user_doc = await db.users.find_one({"reset_token": request.token})
    
    if not user_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    expiration = datetime.fromisoformat(user_doc.get("reset_token_expiration", ""))
    if datetime.now(timezone.utc) > expiration:
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    new_password_hash = hash_password(request.new_password)
    await db.users.update_one(
        {"id": user_doc["id"]},
        {
            "$set": {"password_hash": new_password_hash},
            "$unset": {"reset_token": "", "reset_token_expiration": ""}
        }
    )
    
    return {"message": "Password reset successful"}
