
from fastapi import Request,Depends, Response
from fastapi import APIRouter, Cookie, Depends, Request, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.deps import get_current_user_from_cookie as get_current_user
from jose import JWTError, jwt
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.auth.config import SECRET_KEY, ALGORITHM
from app.core.email import send_reset_email
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.deps import get_current_user_from_cookie
from sqlalchemy.orm import joinedload,Session
from app.db.models import Block, BuddyRequest, Friendship, Guild, GuildMember, Notification, User, UserReport
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
    existing_user = db.query(User).filter(or_(User.username == username, User.email == email)).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username or email already exists"
        })

    hashed_password = pwd_context.hash(password)

    # Generate new user code (e.g., U0001, U0002...)
    last_user = db.query(User).order_by(User.id.desc()).first()
    next_id = (last_user.id + 1) if last_user else 1
    user_code = f"U{next_id:04d}"

    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        user_code=user_code
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/", status_code=302)



@router.get("/")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/")
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    login_input = username.strip().lower()

    user = db.query(User).filter(
        or_(
            User.username.ilike(login_input),
            User.email.ilike(login_input)
        )
    ).first()

    if not user or not pwd_context.verify(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password"
        })

    if getattr(user, "banned", False):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Your account has been banned. Contact support."
        })

    # ✅ Mark user as online and update last active
    user.is_online = True
    user.last_active = datetime.utcnow()
    db.commit()

    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    response = RedirectResponse(
        url="/developer/reports" if getattr(user, "is_developer", False) else "/dashboard",
        status_code=302
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=IS_RENDER,
        max_age=60 * 60 * 24 * 7
    )
    return response

@router.get("/logout")
def logout_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    # ✅ Update user's status to offline
    current_user.is_online = False
    current_user.last_active = datetime.utcnow()
    db.commit()

    # ✅ Clear auth cookie
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("access_token")
    return response



@router.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie),
):
    unread_notif_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read == False
    ).count()

    online_users = db.query(User).filter(User.is_online == True).all()

    now = datetime.utcnow()
    can_claim_daily = (
        not user.last_daily_claim
        or (now - user.last_daily_claim) > timedelta(hours=24)
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": user,
        "user": user,
        "coins": user.coins,
        "level": user.level,
        "xp": user.xp,
        "high_score": user.high_score,
        "unread_notif_count": unread_notif_count,
        "online_users": online_users,
        "now": now,
        "can_claim_daily": can_claim_daily  # ✅ Add this
    })



@router.get("/profile")
def view_profile(
    request: Request,
    db: Session = Depends(get_db),  # ✅ Add DB session
    user: User = Depends(get_current_user_from_cookie),
):
    # ✅ Count unread notifications for the user
    unread_notif_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read == False
    ).count()

    # ✅ Pass unread_notif_count to the template
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "unread_notif_count": unread_notif_count
    })


@router.get("/profile/edit")
def edit_profile_form(request: Request, user: User = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse("edit_profile.html", {"request": request, "user": user})


@router.post("/profile/edit")
def update_profile(
    full_name: str = Form(...),  # required
    bio: str = Form(...),        # required
    avatar: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie)
):
    user.full_name = full_name
    user.bio = bio

    if avatar:
        os.makedirs(AVATAR_DIR, exist_ok=True)
        filename = f"user_{user.id}_{uuid.uuid4().hex}_{avatar.filename.replace(' ', '_')}"
        avatar_path = os.path.join(AVATAR_DIR, filename)
        with open(avatar_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)
        user.avatar_url = f"/{avatar_path}"

    db.commit()
    return RedirectResponse("/profile", status_code=302)


@router.post("/upload-avatar")
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    os.makedirs(AVATAR_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"user_{uuid.uuid4().hex}{ext}"
    path = os.path.join(AVATAR_DIR, unique_filename)

    with open(path, "wb") as f:
        f.write(file.file.read())

    # Save filename to user profile
    current_user.avatar_filename = unique_filename
    db.commit()

    return {"filename": unique_filename}

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


@router.get("/clear-users")
def clear_users(db: Session = Depends(get_db), user: User = Depends(get_current_user_from_cookie)):
    if not user or user.username != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    db.query(User).delete()
    db.commit()
    return {"message": "All users deleted"}

@router.post("/daily-coins")
def claim_daily_coins(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie)
):
    now = datetime.utcnow()
    if user.last_daily_claim and (now - user.last_daily_claim) < timedelta(hours=24):
        return {"error": "You've already claimed daily coins today."}

    user.coins += 100
    user.last_daily_claim = now
    db.commit()
    return {"message": "Claimed 100 coins!", "coins": user.coins}


@router.post("/submit-score")
def submit_score(
    score: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_cookie)
):
    if score > user.high_score:
        user.high_score = score
        db.commit()
    return {"message": "Score submitted", "high_score": user.high_score}


def add_xp(user: User, db: Session, xp_amount: int):
    user.xp += xp_amount
    while user.xp >= user.level * 100:
        user.xp -= user.level * 100
        user.level += 1
    db.commit()


@router.post("/pair-buddy/{user_id}")
def pair_buddy(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot buddy yourself.")

    buddy_user = db.query(User).filter(User.id == user_id).first()
    if not buddy_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if current_user.buddy_id:
        raise HTTPException(status_code=400, detail="You already have a buddy.")

    if buddy_user.buddy_id:
        raise HTTPException(status_code=400, detail="This user is already paired.")

    # Set buddy both ways
    current_user.buddy_id = buddy_user.id
    buddy_user.buddy_id = current_user.id
    db.commit()

    return RedirectResponse(f"/user/{user_id}", status_code=303)

@router.post("/unbuddy")
def unbuddy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    if not current_user.buddy_id:
        raise HTTPException(status_code=400, detail="You don't have a buddy.")

    buddy = db.query(User).filter(User.id == current_user.buddy_id).first()
    if not buddy:
        raise HTTPException(status_code=404, detail="Buddy not found.")

    # Unset both users' buddy_id
    current_user.buddy_id = None
    buddy.buddy_id = None
    db.commit()

    return RedirectResponse(f"/user/{buddy.id}", status_code=303)
@router.post("/buddy/send/{receiver_id}")
def send_buddy_request(
    receiver_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    if current_user.id == receiver_id:
        raise HTTPException(status_code=400, detail="Cannot buddy yourself.")
    
    receiver = db.query(User).filter(User.id == receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if current_user.buddy_id or receiver.buddy_id:
        raise HTTPException(status_code=400, detail="One of the users already has a buddy.")

    existing_request = db.query(BuddyRequest).filter_by(sender_id=current_user.id, receiver_id=receiver_id).first()
    if existing_request:
        raise HTTPException(status_code=400, detail="Buddy request already sent.")

    buddy_request = BuddyRequest(sender_id=current_user.id, receiver_id=receiver_id)
    db.add(buddy_request)
    db.commit()
    return {"message": "Buddy request sent."}


@router.post("/buddy/accept/{sender_id}")
def accept_buddy_request(
    sender_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    req = db.query(BuddyRequest).filter_by(sender_id=sender_id, receiver_id=current_user.id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Buddy request not found.")
    
    sender = db.query(User).filter(User.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found.")

    if current_user.buddy_id or sender.buddy_id:
        raise HTTPException(status_code=400, detail="One of the users already has a buddy.")

    current_user.buddy_id = sender.id
    sender.buddy_id = current_user.id
    db.delete(req)
    db.commit()

    return {"message": "You are now buddies!"}


@router.post("/buddy/reject/{sender_id}")
def reject_buddy_request(
    sender_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    req = db.query(BuddyRequest).filter_by(sender_id=sender_id, receiver_id=current_user.id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Buddy request not found.")

    db.delete(req)
    db.commit()

    return {"message": "Buddy request rejected."}


@router.get("/buddy-requests", response_class=HTMLResponse)
def view_buddy_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    requests = db.query(BuddyRequest).filter(
        BuddyRequest.receiver_id == current_user.id,
        BuddyRequest.status == "pending"
    ).all()
    return templates.TemplateResponse("buddy_requests.html", {
        "request": Request,
        "buddy_requests": requests,
        "current_user": current_user
    })


@router.get("/users")
def get_all_users(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    return templates.TemplateResponse("user_list.html", {"request": request, "users": users})
from datetime import datetime

@router.get("/user/{user_id}")
def view_profile(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # This gives the logged-in user
):
    # ✅ Update last_active for the current logged-in user
    try:
        current_user.last_active = datetime.utcnow()
        db.commit()
    except Exception as e:
        print("Error updating last_active:", e)

    # Get the user being viewed
    viewed_user = db.query(User).filter(User.id == user_id).first()
    if not viewed_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get joined guild (if any)
    guild_membership = db.query(GuildMember).filter_by(user_id=viewed_user.id).first()
    joined_guild = db.query(Guild).filter_by(id=guild_membership.guild_id).first() if guild_membership else None

    # Get buddy info (if any)
    buddy = db.query(User).filter(User.id == viewed_user.buddy_id).first() if viewed_user.buddy_id else None

    # Check block and friendship status
    is_blocked = db.query(Block).filter_by(
        blocker_id=current_user.id,
        blocked_id=viewed_user.id
    ).first() is not None

    friendship = db.query(Friendship).filter(
        or_(
            (Friendship.user_id == current_user.id) & (Friendship.friend_id == viewed_user.id),
            (Friendship.user_id == viewed_user.id) & (Friendship.friend_id == current_user.id)
        )
    ).first()

    is_friend = friendship.accepted if friendship else False
    has_pending_request = friendship and not friendship.accepted and friendship.user_id == current_user.id
    incoming_request = friendship and not friendship.accepted and friendship.friend_id == current_user.id

    return templates.TemplateResponse("profile_card.html", {
        "request": request,
        "user": viewed_user,
        "buddy": buddy,
        "current_user": current_user,
        "viewed_user": viewed_user,
        "is_blocked": is_blocked,
        "is_friend": is_friend,
        "has_pending_request": has_pending_request,
        "incoming_request": incoming_request,
        "friendship_id": friendship.id if friendship else None,
        "joined_guild": joined_guild,
    })




@router.post("/friends/remove/{friend_id}")
def remove_friend(friend_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_cookie)):
    friendship = db.query(Friendship).filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id)) |
        ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id))
    ).first()

    if friendship:
        db.delete(friendship)
        db.commit()

    return RedirectResponse(url=f"/user/{friend_id}", status_code=303)







@router.post("/block/{blocked_id}")
def block_user(blocked_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_cookie)):
    if blocked_id == current_user.id:
        raise HTTPException(status_code=400, detail="You can't block yourself.")
    
    already_blocked = db.query(Block).filter_by(blocker_id=current_user.id, blocked_id=blocked_id).first()
    if already_blocked:
        raise HTTPException(status_code=400, detail="User already blocked.")
    
    block = Block(blocker_id=current_user.id, blocked_id=blocked_id)
    db.add(block)
    db.commit()
    return RedirectResponse(url=f"/user/{blocked_id}", status_code=303)

@router.post("/unblock/{blocked_id}")
def unblock_user(blocked_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_cookie)):
    block = db.query(Block).filter_by(blocker_id=current_user.id, blocked_id=blocked_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="User not blocked.")
    
    db.delete(block)
    db.commit()
    return RedirectResponse(url=f"/user/{blocked_id}", status_code=303)



@router.get("/users")
def show_users(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    blocked_ids = db.query(Block.blocked_id).filter_by(blocker_id=current_user.id).subquery()
    users = db.query(User).filter(User.id.notin_(blocked_ids)).all()
    return templates.TemplateResponse("user_list.html", {"request": request, "users": users})


@router.post("/report-user")
def report_user(
    request: Request,
    user_id: int = Form(...),
    reason: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    reported_user = db.query(User).filter(User.id == user_id).first()
    if not reported_user:
        raise HTTPException(status_code=404, detail="Reported user not found")

    report = UserReport(
        reported_user_id=reported_user.id,
        reporter_user_id=current_user.id,
        reason=reason
    )
    db.add(report)
    db.commit()
    return RedirectResponse("/dashboard", status_code=302)

@router.get("/online-users", response_class=HTMLResponse)
def show_online_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    threshold = datetime.utcnow() - timedelta(minutes=5)  # show users active in last 5 minutes
    online_users = db.query(User).filter(
        User.is_online == True,
        User.last_active >= threshold
    ).all()

    print("ONLINE USERS:")
    for u in online_users:
        print(f"User {u.id} - {u.username} - Last Active: {u.last_active}")

    return templates.TemplateResponse("online_users.html", {
        "request": request,
        "online_users": online_users,
        "current_user": current_user
    })

@router.post("/claim-daily")
def claim_daily_coins(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    now = datetime.utcnow()
    if current_user.last_daily_claim and (now - current_user.last_daily_claim) < timedelta(hours=24):
        return RedirectResponse(url="/dashboard", status_code=302)

    current_user.coins += 50  # 🎁 Award daily coins
    current_user.last_daily_claim = now
    db.commit()

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("daily_claimed", "1", max_age=5)
    return response








