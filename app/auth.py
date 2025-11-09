from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import hashlib
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv

from .schemas import TokenData
from .models import User

load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

security = HTTPBearer()


def verify_password(plain_password, hashed_password):
    """Simple password verification using SHA256 with salt"""
    try:
        # Extract salt and hash from stored password
        salt, stored_hash = hashed_password.split("$")
        # Hash the plain password with the same salt
        computed_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
        return computed_hash == stored_hash
    except:
        return False


def get_password_hash(password):
    """Simple password hashing using SHA256 with salt"""
    salt = secrets.token_hex(16)  # 16 bytes of random salt
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${password_hash}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token():
    """Create a secure random refresh token"""
    return secrets.token_urlsafe(32)


def get_refresh_token_hash(refresh_token: str):
    """Hash refresh token for secure storage"""
    return get_password_hash(refresh_token)


def verify_refresh_token(refresh_token: str, token_hash: str):
    """Verify refresh token against stored hash"""
    return verify_password(refresh_token, token_hash)


async def authenticate_user(db, email: str, password: str):
    """Authenticate user by email and password"""
    from . import crud

    user = await crud.get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=None,  # Database session will be injected
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    # Query the database for the actual user
    if db is None:
        raise credentials_exception

    # Import crud here to avoid circular imports
    from . import crud

    user = await crud.get_user_by_email(db, token_data.email)

    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user
