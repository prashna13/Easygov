"""
auth_utils.py
-------------
Authentication helpers: password hashing with bcrypt, JWT token creation,
and FastAPI dependencies for token verification.
"""

import logging
import os
import secrets
from pathlib import Path
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

# ── JWT CONFIGURATION ─────────────────────────────────────────────────────────
# Prefer an explicit env secret (stable, for production). Otherwise, generate one
# once and persist it under gitignored db_storage/ so that signing stays stable
# across restarts — otherwise every restart invalidates all currently-issued
# tokens and the app surfaces 401 errors everywhere.
_STORAGE_DIR = Path("db_storage")
_JWT_SECRET_FILE = _STORAGE_DIR / "jwt_secret"


def _load_or_create_jwt_secret() -> str:
    env_secret = os.getenv("JWT_SECRET_KEY")
    if env_secret:
        return env_secret
    if _JWT_SECRET_FILE.exists():
        return _JWT_SECRET_FILE.read_text().strip()
    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    generated = secrets.token_urlsafe(48)
    _JWT_SECRET_FILE.write_text(generated)
    logger.warning(
        "JWT_SECRET_KEY is not set — generated and persisted a secret at %s so "
        "tokens survive restarts. Back this file up, or set JWT_SECRET_KEY in "
        "production, or all sessions will be invalidated if it is lost.",
        _JWT_SECRET_FILE,
    )
    return generated


SECRET_KEY = _load_or_create_jwt_secret()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ── PASSWORD HASHING (DIRECT BCRYPT) ──────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ── JWT GENERATION & DECODING ────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token containing subject claims."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Returns the authenticated User object if a valid Bearer token is provided, or None."""
    if not token:
        return None

    # Handle optional "Bearer " prefix
    if token.startswith("Bearer "):
        token = token[7:]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Requires a valid Bearer token; raises HTTP 401 if missing or invalid."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    if token.startswith("Bearer "):
        token = token[7:]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if user is None:
        raise credentials_exception

    return user
