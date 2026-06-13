import uuid
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.database import get_db
from app.models import User, Organization, EmailVerificationToken, PasswordResetToken
from app.config import settings
from app.services.email import send_welcome_email, send_password_reset_email

logger = logging.getLogger("contract-review.auth")
router = APIRouter(prefix="/auth", tags=["auth"])
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc) + expires_delta, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# --- Schemas ---

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    organization_name: str
    gstin: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    organization_id: str
    role: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# --- Endpoints ---

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    org = Organization(name=req.organization_name, gstin=req.gstin or None, email=req.email)
    db.add(org)
    db.flush()

    user = User(
        email=req.email,
        password_hash=pwd.hash(req.password),
        full_name=req.full_name,
        organization_id=org.id,
        role="admin",
    )
    db.add(user)
    db.flush()

    vt = EmailVerificationToken(
        user_id=user.id,
        token=str(uuid.uuid4()),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(vt)
    db.commit()
    db.refresh(user)

    verify_url = f"{settings.app_url}/verify-email?token={vt.token}"
    send_welcome_email(user.email, user.full_name, verify_url)

    logger.info("User registered: %s (org: %s)", user.email, org.name)
    return {"message": "Registration successful. Please check your email to verify your account.", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not pwd.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_token(
        {"sub": user.id, "org": user.organization_id, "role": user.role},
        timedelta(minutes=settings.jwt_expire_minutes),
    )
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
    )


@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest, db: Session = Depends(get_db)):
    vt = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == req.token,
        EmailVerificationToken.used == False,
        EmailVerificationToken.expires_at > datetime.now(timezone.utc),
    ).first()
    if not vt:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    vt.used = True
    user = db.query(User).filter(User.id == vt.user_id).first()
    if user:
        user.is_verified = True
    db.commit()
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"message": "If the email exists, a reset link has been sent."}

    rt = PasswordResetToken(
        user_id=user.id,
        token=str(uuid.uuid4()),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(rt)
    db.commit()

    reset_url = f"{settings.app_url}/reset-password?token={rt.token}"
    send_password_reset_email(user.email, user.full_name, reset_url)

    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    rt = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == req.token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.now(timezone.utc),
    ).first()
    if not rt:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    rt.used = True
    user = db.query(User).filter(User.id == rt.user_id).first()
    if user:
        user.password_hash = pwd.hash(req.password)
    db.commit()
    return {"message": "Password reset successful. You can now log in with your new password."}


def get_current_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    payload = verify_token(auth[7:])
    return payload.get("sub", "")


def get_current_org_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    payload = verify_token(auth[7:])
    org_id = payload.get("org", "")
    if not org_id:
        raise HTTPException(status_code=401, detail="No organization found in token")
    return org_id
