from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_

from app.core.deps import get_current_user_from_cookie
from app.core.database import get_db
from app.db import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/list")
def friends_list(
    request: Request,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    Friend = aliased(models.User)
    friends = (
        db.query(Friend)
        .join(
            models.Friendship,
            models.Friendship.friend_id == Friend.id
        )
        .filter(
            models.Friendship.user_id == user.id,
            models.Friendship.accepted == True
        )
        .all()
    )
    return templates.TemplateResponse(
        "friends.html",
        {"request": request, "friends": friends}
    )


@router.get("/add")
def add_friend_form(request: Request):
    """
    Render the “add friend” form. If there was a previous error, it will
    be passed as “error” in the template context.
    """
    return templates.TemplateResponse("add_friend.html", {"request": request, "error": None})

@router.post("/add-by-code")
def add_friend_by_code(
    user_code: str = Form(None),
    username: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    if not user_code and not username:
        raise HTTPException(status_code=400, detail="Provide either user code or username.")

    filters = []
    if user_code:
        filters.append(models.User.user_code == user_code.strip())
    if username:
        filters.append(models.User.username == username.strip())

    friend = db.query(models.User).filter(or_(*filters)).first()

    if not friend or friend.id == current_user.id:
        raise HTTPException(status_code=400, detail="User not found or invalid.")

    existing = db.query(models.Friendship).filter(
        or_(
            (models.Friendship.user_id == current_user.id) & (models.Friendship.friend_id == friend.id),
            (models.Friendship.user_id == friend.id) & (models.Friendship.friend_id == current_user.id)
        )
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Friend request already exists.")

    db.add(models.Friendship(
        user_id=current_user.id,
        friend_id=friend.id,
        accepted=False
    ))
    db.commit()

    return RedirectResponse("/friends/list", status_code=303)




@router.get("/requests")
def friend_requests(
    request: Request,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    Requester = aliased(models.User)
    pending = (
        db.query(models.Friendship)
        .filter(
            models.Friendship.friend_id == user.id,
            models.Friendship.accepted == False
        )
        .join(Requester, Requester.id == models.Friendship.user_id)
        .all()
    )

    request_data = []
    for friendship in pending:
        from_user = db.query(models.User).get(friendship.user_id)
        request_data.append({
            "id": friendship.id,
            "from_username": from_user.username,
            "from_user_code": from_user.user_code  # <== Add this
        })

    return templates.TemplateResponse(
        "friend_requests.html",
        {"request": request, "requests": request_data}
    )


@router.post("/accept/{friendship_id}")
def accept_friend(
    friendship_id: int,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Try to find the friend request
    friendship = db.query(models.Friendship).filter(
        models.Friendship.id == friendship_id
    ).first()

    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found.")

    # Check who is trying to accept
    if friendship.friend_id != user.id:
        raise HTTPException(status_code=403, detail="You are not the recipient of this friend request.")

    if friendship.accepted:
        raise HTTPException(status_code=400, detail="This friend request has already been accepted.")

    # Accept the request
    friendship.accepted = True
    db.commit()

    # Create reciprocal friendship if not already present
    reverse_exists = db.query(models.Friendship).filter_by(
        user_id=friendship.friend_id,
        friend_id=friendship.user_id,
        accepted=True
    ).first()

    if not reverse_exists:
        reverse = models.Friendship(
            user_id=friendship.friend_id,
            friend_id=friendship.user_id,
            accepted=True
        )
        db.add(reverse)
        db.commit()

    return RedirectResponse("/friends/requests", status_code=303)


@router.post("/unfriend/{friend_id}")
def unfriend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    """
    Remove an existing friendship (both directions). Only allowed if there
    is an accepted==True row in at least one direction.
    """
    friendships = (
        db.query(models.Friendship)
        .filter(
            or_(
                (models.Friendship.user_id == current_user.id) & (models.Friendship.friend_id == friend_id),
                (models.Friendship.user_id == friend_id) & (models.Friendship.friend_id == current_user.id)
            ),
            models.Friendship.accepted == True
        )
        .all()
    )

    if not friendships:
        raise HTTPException(status_code=404, detail="Friendship not found")

    for f in friendships:
        db.delete(f)
    db.commit()

    return RedirectResponse("/friends/list", status_code=303)

@router.post("/add-friend/{user_id}")
def add_friend_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot add yourself.")

    friend = db.query(models.User).filter(models.User.id == user_id).first()
    if not friend:
        raise HTTPException(status_code=404, detail="User not found.")

    # Check if friendship already exists
    existing = db.query(models.Friendship).filter(
        or_(
            (models.Friendship.user_id == current_user.id) & (models.Friendship.friend_id == friend.id),
            (models.Friendship.user_id == friend.id) & (models.Friendship.friend_id == current_user.id)
        )
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Friend request already exists.")

    new_friendship = models.Friendship(
        user_id=current_user.id,
        friend_id=friend.id,
        accepted=False
    )
    db.add(new_friendship)
    db.commit()
    return RedirectResponse(f"/user/{user_id}", status_code=303)
