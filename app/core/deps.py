from fastapi import Cookie, Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import User
from app.auth.config import SECRET_KEY, ALGORITHM

def get_current_user_from_cookie(
    access_token: str = Cookie(None),  # ✅ Must match cookie key
    db: Session = Depends(get_db)
) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail="No token found")

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
