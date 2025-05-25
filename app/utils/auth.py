import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import HTTPException, status, Request
from jose import JWTError, jwt

# Load .env variables
load_dotenv()

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TOKEN_EXPIRE_DAYS = int(os.getenv("TOKEN_EXPIRE_DAYS", "30"))

# Load valid API keys from environment
API_KEYS = [key.strip() for key in os.getenv("API_KEYS", "").split(",") if key.strip()]


def create_jwt_token(api_key: str) -> str:
    """
    Generate a JWT token with api_key as subject.
    """
    payload = {
        "sub": api_key,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_and_validate_token(token: str) -> str:
    """
    Decode JWT token and validate its `sub` (API key).
    Returns the API key if valid, else raises HTTPException.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        api_key = payload.get("sub")
        if not api_key or api_key not in API_KEYS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token or API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return api_key
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def authenticate_request(request: Request) -> str:
    """
    Dependency to authenticate any route.
    Verifies JWT from Authorization header and returns the API key.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.removeprefix("Bearer ").strip()
    return decode_and_validate_token(token)
