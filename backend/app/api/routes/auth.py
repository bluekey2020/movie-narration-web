"""Authentication API — JWT-based login/register."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.config import settings

router = APIRouter()

# ===== Security =====

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 1 week


# ===== In-memory user store (MVP — replace with DB in production) =====

_users: dict[str, dict] = {}


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        'sub': user_id,
        'email': email,
        'exp': expire,
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def get_current_user(authorization: str = Header(None)) -> dict:
    """FastAPI dependency: extract current user from Bearer token.

    Usage:
        @app.get('/me')
        async def me(user: dict = Depends(get_current_user)):
            return user
    """
    if not authorization:
        raise HTTPException(status_code=401, detail='Missing authorization header')

    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=401, detail='Invalid authorization header')

    payload = _decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

    user_id = payload.get('sub')
    user = _users.get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail='User not found')

    return {
        'user_id': user['user_id'],
        'email': user['email'],
        'display_name': user['display_name'],
        'plan': user.get('plan', 'free'),
        'credits_remaining': user.get('credits_remaining', 100),
        'monthly_videos_used': user.get('monthly_videos_used', 0),
        'monthly_videos_limit': user.get('monthly_videos_limit', 3),
    }


# ===== Request/Response models =====

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    plan: str
    credits_remaining: int
    monthly_videos_used: int
    monthly_videos_limit: int


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# ===== Routes =====

@router.post('/register', response_model=AuthResponse)
async def register(data: RegisterRequest):
    """Register a new user account."""
    import uuid

    # Check if email already exists
    for u in _users.values():
        if u['email'] == data.email:
            raise HTTPException(status_code=409, detail='Email already registered')

    user_id = str(uuid.uuid4())
    user = {
        'user_id': user_id,
        'email': data.email,
        'display_name': data.display_name,
        'password_hash': _hash_password(data.password),
        'plan': 'free',
        'credits_remaining': 100,
        'monthly_videos_used': 0,
        'monthly_videos_limit': 3,
        'created_at': datetime.utcnow().isoformat(),
    }
    _users[user_id] = user

    token = _create_token(user_id, data.email)

    return AuthResponse(
        token=token,
        user=UserResponse(
            user_id=user_id,
            email=data.email,
            display_name=data.display_name,
            plan='free',
            credits_remaining=100,
            monthly_videos_used=0,
            monthly_videos_limit=3,
        ),
    )


@router.post('/login', response_model=AuthResponse)
async def login(data: LoginRequest):
    """Login with email and password."""
    # Find user by email
    user = None
    for u in _users.values():
        if u['email'] == data.email:
            user = u
            break

    if not user:
        raise HTTPException(status_code=401, detail='Invalid email or password')

    if not _verify_password(data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid email or password')

    token = _create_token(user['user_id'], data.email)

    return AuthResponse(
        token=token,
        user=UserResponse(
            user_id=user['user_id'],
            email=user['email'],
            display_name=user['display_name'],
            plan=user.get('plan', 'free'),
            credits_remaining=user.get('credits_remaining', 100),
            monthly_videos_used=user.get('monthly_videos_used', 0),
            monthly_videos_limit=user.get('monthly_videos_limit', 3),
        ),
    )


@router.get('/me', response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(**user)
