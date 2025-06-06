from fastapi import APIRouter, Cookie, Depends, Request, Form, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.auth.config import SECRET_KEY, ALGORITHM
from app.core.email import send_reset_email
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.deps import get_current_user_from_cookie
from app.db.models import User
import os
import shutil
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
IS_RENDER = os.getenv("RENDER") == "true"
AVATAR_DIR = "static/avatars"

@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username or email already exists"
        })

    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/", status_code=302)



@router.get("/")
def login_form(request: Request, token: str = Cookie(None)):
    if token:
        try:
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return RedirectResponse("/dashboard")
        except JWTError:
            pass
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/")
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        or_(User.username == username, User.email == username)
    ).first()

    if not user or not pwd_context.verify(password, User.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })

    token = create_access_token(
        data={"sub": User.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=IS_RENDER
    )
    return response

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


@router.get("/profile")
def view_profile(request: Request, user: User = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@router.get("/profile/edit")
def edit_profile_form(request: Request, user: User = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("edit_profile.html", {"request": request, "user": user})

@router.post("/profile/edit")
def update_profile(
    request: Request,
    full_name: str = Form(...),
    bio: str = Form(...),
    avatar: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie)
):
    user.full_name = full_name
    user.bio = bio

    if avatar:
        os.makedirs(AVATAR_DIR, exist_ok=True)
        avatar_path = os.path.join(AVATAR_DIR, f"user_{user.id}_{avatar.filename}")
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)
        user.avatar_url = f"/{avatar_path}"

    db.commit()
    return RedirectResponse("/profile", status_code=302)

@router.get("/forgot-password")
def forgot_password_form(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.post("/forgot-password")
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = str(uuid.uuid4())
        user.reset_token = token
        user.reset_token_expires = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        send_reset_email(user.email, token)
    return templates.TemplateResponse("forgot_password.html", {
        "request": request,
        "message": "If the email exists, a reset link has been sent."
    })

@router.get("/reset-password")
def reset_password_form(request: Request, token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@router.post("/reset-password")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user or user.reset_token_expires < datetime.utcnow():
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "token": token,
            "error": "Token is invalid or expired."
        })

    user.hashed_password = pwd_context.hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return RedirectResponse(url="/", status_code=302)

@router.get("/protected")
def protected_route(user: User = Depends(get_current_user_from_cookie)):
    return {"user": user.username}
