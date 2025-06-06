# app/core/deps.py
from fastapi import Cookie, Depends, HTTPException
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.config import SECRET_KEY, ALGORITHM
from app.db import models

def get_current_user_from_cookie(
    db: Session = Depends(get_db),
    token: str = Cookie(None, alias="access_token")
) -> models.User:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
