"""
google_auth.py
--------------
Google Sign-In for EasyGov Nepal — "Continue with Google".

The Android app runs Google Sign-In (play-services-auth) and receives an
ID token whose audience is the *Web* OAuth client ID passed to
`GoogleSignInOptions.requestIdToken(...)`. The client POSTs that ID token
here; the server verifies its signature and audience with the official
`google-auth` library, then authenticates the user (auto-creating the
account on first sign-in).

Config (env):
    GOOGLE_OAUTH_WEB_CLIENT_ID   The Web OAuth client ID from Google Cloud
                                 Console (placeholder until you fill it in).

Router: POST /auth/google
"""

import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth_utils import create_access_token, hash_password
from app.database import get_db
from app.models import User
from app.schemas import GoogleLogin, TokenResponse, UserOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth-google"])


def get_google_web_client_id() -> str:
    """Web OAuth client ID that must match the ID token's `aud` claim."""
    return os.getenv("GOOGLE_OAUTH_WEB_CLIENT_ID", "").strip()


def verify_google_id_token(token: str) -> dict:
    """Verify a Google Sign-In ID token and return its claims.

    Raises HTTPException(401) if the server is not configured, the token is
    malformed/expired/wrong-audience, or the Google email is unverified.
    """
    client_id = get_google_web_client_id()
    if not client_id:
        logger.warning("GOOGLE_OAUTH_WEB_CLIENT_ID is not set — Google Sign-In disabled")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Sign-In is not configured on the server.",
        )

    try:
        request = google_requests.Request()
        claims = id_token.verify_oauth2_token(token, request, client_id)
    except Exception:
        logger.warning("Rejected invalid Google ID token", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token.",
        ) from None

    if claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email is not verified.",
        )
    return claims


@router.post("/google", response_model=TokenResponse)
def google_login(payload: GoogleLogin, db: Session = Depends(get_db)):
    """Authenticate (or auto-register) a user with a verified Google ID token."""
    claims = verify_google_id_token(payload.id_token)

    email = (claims.get("email") or "").strip().lower()
    google_sub = claims.get("sub")
    full_name = (claims.get("name") or "").strip()[:200] or email

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account has no email address.",
        )

    # Match by email (links Google to a pre-existing password account on
    # first Google sign-in) or by google_id (already-linked account).
    user = db.query(User).filter(or_(User.email == email, User.google_id == google_sub)).first()

    if user is None:
        # New user — Google account becomes their EasyGov account. A random
        # secret is hashed into password_hash so the field stays NOT NULL and
        # any password attempt cleanly fails (this user signs in via Google).
        user = User(
            email=email,
            google_id=google_sub,
            full_name=full_name,
            password_hash=hash_password(str(uuid.uuid4())),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.google_id and google_sub and user.google_id != google_sub:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Google account is linked to a different EasyGov account.",
        )
    elif not user.google_id and google_sub:
        user.google_id = google_sub
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token, token_type="bearer", user=UserOut.model_validate(user))