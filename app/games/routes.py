from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user_from_cookie
from app.db import models
from app.games.schemas import RoomCreate, RoomOut

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/rooms/create")
def create_room_form(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    return templates.TemplateResponse("create-room.html", {
        "request": request,
        "user": current_user
    })

# POST: Handle form submission
@router.post("/rooms/create")
def create_room_post(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    # Check if room already exists
    existing = db.query(models.GameRoom).filter(models.GameRoom.name == name).first()
    if existing:
        return templates.TemplateResponse("create-room.html", {
            "request": request,
            "user": current_user,
            "error": "Room name already exists"
        })

    # Create room
    room = models.GameRoom(
        name=name,
        description=description,
        created_by=current_user.id
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    # Redirect to the room page
    return RedirectResponse(f"/game-room/{room.id}", status_code=303)

# ✅ List Rooms
@router.get("/game-room")
def list_rooms(
    request: Request,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    rooms = db.query(models.GameRoom).all()
    return templates.TemplateResponse("game_room_list.html", {
        "request": request,
        "user": user,
        "rooms": rooms
    })

# ✅ Room Details
@router.get("/game-room/{room_id}")
def room_detail(
    request: Request,
    room_id: int,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return templates.TemplateResponse("game_room.html", {
        "request": request,
        "user": user,
        "room": room
    })

# ✅ Get Chat Messages
@app.get("/game-chat/{room_id}", response_class=HTMLResponse)
async def chat_room_view(request: Request, room_id: int, user=Depends(get_current_user)):
    room = get_room_by_id(room_id)
    messages = room.messages  # Or query messages separately
    return templates.TemplateResponse("chat_room.html", {
        "request": request,
        "room": room,
        "messages": messages,
        "user": user,
    })

# ✅ Post Chat Message
@router.post("/game-chat/{room_id}/chat")
def post_chat_message(
    request: Request,
    room_id: int,
    content: str = Form(...),
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Game room not found")
    new_message = models.Message(
        room_id=room_id,
        sender_id=user.id,
        content=content,
        timestamp=datetime.utcnow()
    )
    db.add(new_message)
    db.commit()
    return RedirectResponse(url=f"/game-chat/{room_id}/chat", status_code=303)

@router.get("/games/piano", response_class=HTMLResponse)
def piano_game(request: Request):
    return templates.TemplateResponse("piano.html", {"request": request})

@app.post("/game-room/{room_id}/kick/{user_id}")
async def kick_user(room_id: int, user_id: int, user=Depends(get_current_user)):
    # Kick logic here
    return RedirectResponse(f"/game-chat/{room_id}", status_code=303)
