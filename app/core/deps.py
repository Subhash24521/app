from fastapi import Cookie, HTTPException, Depends
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.models import User
from app.auth.config import SECRET_KEY, ALGORITHM

def get_current_user_from_cookie(token: str = Cookie(None), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="No token found")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
