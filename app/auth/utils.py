from app.core.security import get_password_hash, verify_password, create_access_token
from datetime import timedelta
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES

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
