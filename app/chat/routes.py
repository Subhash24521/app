# app/chat/routes.py

import os
from datetime import datetime, timedelta, date

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    HTTPException,
    status,
)
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_

from app.core.database import get_db
from app.core.deps import get_current_user_from_cookie
from app.db import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# === CONFIGURABLE CONSTANTS ===
# How many messages each user may post per room per 24-hour window
MAX_MESSAGES_PER_DAY = 50

# === HELPERS ===

def ensure_room_not_expired(db: Session, room_id: int):
    """
    Check if the given room exists and is not older than 24h.
    If it is expired (created_at + 24h < now), delete it (and its messages)
    and raise a 404. Otherwise return the room object.
    """
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Game room not found")

    # Has 24 hours passed since creation?
    expiration_time = room.created_at + timedelta(hours=24)
    now = datetime.utcnow()
    if now >= expiration_time:
        # Delete room and all its messages via cascade
        db.delete(room)
        db.commit()
        raise HTTPException(status_code=404, detail="Game room has expired")

    return room


# === ROUTES ===
@router.get("/game-chat/{room_id}/chat")
def get_chat_messages(
    request: Request,
    room_id: int,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    try:
        room = ensure_room_not_expired(db, room_id)
    except HTTPException:
        # Room was expired (deleted). Redirect to /games instead of 404.
        return RedirectResponse(url="/games", status_code=303)

    messages = (
        db.query(models.Message)
        .options(joinedload(models.Message.sender))
        .filter(models.Message.room_id == room_id)
        .order_by(models.Message.timestamp.asc())
        .all()
    )

    return templates.TemplateResponse(
        "chat_room.html", {"request": request, "room": room, "messages": messages}
    )

@router.post("/game-chat/{room_id}/chat")
def post_chat_message(
    request: Request,
    room_id: int,
    content: str = Form(...),
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    try:
        room = ensure_room_not_expired(db, room_id)
    except HTTPException:
        # Room expired → redirect
        return RedirectResponse(url="/games", status_code=303)

    # Enforce per-user daily limit
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_count = (
        db.query(func.count(models.Message.id))
        .filter(
            models.Message.room_id == room_id,
            models.Message.sender_id == user.id,
            models.Message.timestamp >= cutoff,
        )
        .scalar()
        or 0
    )

    if recent_count >= MAX_MESSAGES_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Daily message limit ({MAX_MESSAGES_PER_DAY}) reached in this room.",
        )

    new_message = models.Message(
        room_id=room_id,
        sender_id=user.id,
        content=content,
        timestamp=datetime.utcnow(),
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return RedirectResponse(url=f"/game-chat/{room_id}/chat", status_code=303)

@router.post("/game-chat/{room_id}/exit")
def exit_chat_room(
    request: Request,
    room_id: int,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()

    if not room:
        return RedirectResponse(url="/games", status_code=303)

    if datetime.utcnow() >= room.created_at + timedelta(hours=24):
        db.delete(room)
        db.commit()
        return RedirectResponse(url="/game-room", status_code=303)

    if room.created_by == user.id:  # <-- fixed line
        db.delete(room)
    else:
        db.query(models.Message).filter(
            models.Message.room_id == room_id,
            models.Message.sender_id == user.id
        ).delete()

    db.commit()
    return RedirectResponse(url="/game-room", status_code=303)


