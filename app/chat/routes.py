from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user_from_cookie
from app.db import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Show chat messages for a game room
@router.get("/game-chat/{room_id}/chat")
def get_chat_messages(
    request: Request,
    room_id: int,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Verify room exists
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Game room not found")

    # Load messages for the room, ordered by timestamp ascending
    messages = db.query(models.Message).filter(models.Message.room_id == room_id).order_by(models.Message.timestamp.asc()).all()

    return templates.TemplateResponse("chat_room.html", {
        "request": request,
        "user": user,
        "room": room,
        "messages": messages
    })

# Post a new chat message to a room
@router.post("/game-chat/{room_id}/chat")
def post_chat_message(
    request: Request,
    room_id: int,
    content: str = Form(...),
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    # Verify room exists
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Game room not found")

    # Create message
    new_message = models.Message(
        room_id=room_id,
        sender_id=user.id,
        content=content,
        timestamp=datetime.utcnow()
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Redirect back to chat page after posting message
    return RedirectResponse(url=f"/game-chat/{room_id}/chat", status_code=303)
