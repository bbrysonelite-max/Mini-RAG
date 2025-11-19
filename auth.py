"""
Google OAuth 2.0 authentication module for Mini-RAG.
Handles OAuth flow, JWT token generation/validation, and user session management.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from jose import JWTError, jwt
from dotenv import load_dotenv

# Load environment variables (support both standard runs and stdin-launched scripts)
PROJECT_ROOT = Path(__file__).resolve().parent
DOTENV_PATH = PROJECT_ROOT / ".env"
if DOTENV_PATH.exists():
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    # Fall back to default discovery so containerized deployments can inject values
    load_dotenv()

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# OAuth configuration
GOOGLE_CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Initialize OAuth (only if credentials are provided)
oauth = OAuth()
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=GOOGLE_CONF_URL,
        client_kwargs={
            "scope": "openid email profile"
        }
    )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY not configured. Please set it in .env file.")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token."""
    try:
        if not SECRET_KEY:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Get user information from a JWT token."""
    payload = verify_token(token)
    if payload is None:
        return None
    return {
        "email": payload.get("email"),
        "name": payload.get("name"),
        "picture": payload.get("picture"),
        "sub": payload.get("sub"),
        "user_id": payload.get("user_id"),  # UUID from database
        "role": payload.get("role", "reader")  # Default to reader
    }


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current authenticated user from request."""
    # Check for token in cookie
    token = request.cookies.get("access_token")
    if not token:
        # Check for token in Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
    
    return get_user_from_token(token)


def require_auth(request: Request) -> Dict[str, Any]:
    """Dependency to require authentication. Raises HTTPException if not authenticated.
    Usage: @app.get("/protected"); def protected_route(user: dict = Depends(require_auth)):
    """
    from fastapi import HTTPException, status
    
    user = get_current_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

