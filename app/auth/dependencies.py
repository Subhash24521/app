from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.auth.utils import decode_token
from app.db.models import User
from app.core.database import get_db  # or wherever your get_db is defined

def get_current_user_from_cookie(
    request: Request, 
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
