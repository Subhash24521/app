from app.core.security import get_password_hash, verify_password, create_access_token
from datetime import datetime, timedelta
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.db.models import Block
from fastapi import HTTPException, status

import jwt  # From PyJWT
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

def authenticate_user(db, username: str, password: str):
    user = db.query(db.models.User).filter_by(username=username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_user(db, username: str, password: str):
    hashed = get_password_hash(password)
    user = db.models.User(username=username, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError
from fastapi import HTTPException, status

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error decoding token",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def is_blocked(user1_id: int, user2_id: int, db):
    return db.query(Block).filter(
        ((Block.blocker_id == user1_id) & (Block.blocked_id == user2_id)) |
        ((Block.blocker_id == user2_id) & (Block.blocked_id == user1_id))
    ).first() is not None

from fastapi import Request

def update_last_active(request: Request, db, user):
    ip = request.client.host  # ✅ correct way
    user.last_active = datetime.utcnow()
    db.commit()
