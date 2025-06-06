from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.config import SECRET_KEY, ALGORITHM
from app.core.database import get_db
from app.db.models import User

def get_current_user_from_cookie(
    access_token: str = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
