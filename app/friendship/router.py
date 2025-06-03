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


@router.post("/add")
def add_friend(
    request: Request,
    friend_username: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    """
    Handle the “add friend” form POST. We only create a new Friendship if:
      - friend_username matches a real user (and is not the current user)
      - there is no existing Friendship row (pending or accepted) between them
    Otherwise, re-render the form with an error message.
    """
    friend_username = friend_username.strip()

    # 1. Check that the entered username exists and is not the current user
    friend = db.query(models.User).filter(models.User.username == friend_username).first()
    if not friend or friend.id == current_user.id:
        # Username not found or user tried to add themselves
        error_msg = "User not found."
        return templates.TemplateResponse(
            "add_friend.html",
            {"request": request, "error": error_msg}
        )

    # 2. Check for any existing Friendship (either direction, accepted or not)
    existing = (
        db.query(models.Friendship)
        .filter(
            or_(
                (models.Friendship.user_id == current_user.id) & (models.Friendship.friend_id == friend.id),
                (models.Friendship.user_id == friend.id) & (models.Friendship.friend_id == current_user.id)
            )
        )
        .first()
    )

    if existing:
        if existing.accepted:
            error_msg = "You are already friends with “{}”.".format(friend_username)
        else:
            # There is a pending request in one direction
            if existing.user_id == current_user.id:
                error_msg = f"You have already sent a friend request to “{friend_username}.”"
            else:
                error_msg = f"“{friend_username}” has already sent you a friend request."
        return templates.TemplateResponse(
            "add_friend.html",
            {"request": request, "error": error_msg}
        )

    # 3. Otherwise, everything is valid: create a new (pending) friendship
    new_friendship = models.Friendship(
        user_id=current_user.id,
        friend_id=friend.id,
        accepted=False
    )
    db.add(new_friendship)
    db.commit()

    # Redirect back to the friends list (or requests page)
    return RedirectResponse("/friends/list", status_code=303)


@router.get("/requests")
def friend_requests(
    request: Request,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """
    Show all pending friend requests where current_user is the “friend_id”
    and accepted == False.
    """
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

    # Build a simple list for the template
    request_data = []
    for friendship in pending:
        from_user = db.query(models.User).get(friendship.user_id)
        request_data.append({
            "id": friendship.id,
            "from_username": from_user.username
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
    """
    Accept an incoming friend request. We mark the record accepted=True,
    then also create a reciprocal accepted=True row so that each user sees
    each other as friends.
    """
    friendship = (
        db.query(models.Friendship)
        .filter(
            models.Friendship.id == friendship_id,
            models.Friendship.friend_id == user.id,
            models.Friendship.accepted == False
        )
        .first()
    )
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")

    # Mark this request accepted
    friendship.accepted = True
    db.commit()

    # Create reciprocal “accepted” relationship
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
