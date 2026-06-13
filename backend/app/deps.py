from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database import get_db
from app.config import settings
from app.models import User, Organization, Subscription


def require_org(request: Request) -> str:
    """Extract organization_id from JWT token in Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    try:
        payload = jwt.decode(auth[7:], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    org_id = payload.get("org", "")
    if not org_id:
        raise HTTPException(status_code=401, detail="No organization found in token")
    return org_id


def require_user(request: Request) -> str:
    """Extract user_id from JWT token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    try:
        payload = jwt.decode(auth[7:], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


def check_contract_limit(org_id: str, db: Session) -> None:
    sub = db.query(Subscription).filter(
        Subscription.organization_id == org_id,
        Subscription.status.in_(["active", "trial"]),
    ).first()
    if sub and sub.plan:
        if sub.contract_count >= sub.plan.max_contracts:
            raise HTTPException(
                status_code=403,
                detail=f"Contract limit reached ({sub.plan.max_contracts}). Upgrade your plan to upload more contracts.",
            )
