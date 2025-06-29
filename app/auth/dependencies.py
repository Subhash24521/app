from fastapi import Request, HTTPException, Depends
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.db.models import User
from app.core.config import SECRET_KEY, ALGORITHM
from app.core.database import get_db

def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    print(">>> Cookie Received:", token)  # ✅ Check terminal output
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")


    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        print("DECODED USERNAME:", username)  # Debug line

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError as e:
        print("JWT ERROR:", e)  # Debug line
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
