from fastapi import APIRouter, Depends, Request, Form, HTTPException,status
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
    db: Session = Depends(get_db),  # ✅ Add database session
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    # ✅ Fetch unread notifications count
    unread_notif_count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.read == False
    ).count()

    return templates.TemplateResponse("create-room.html", {
        "request": request,
        "user": current_user,
        "unread_notif_count": unread_notif_count  # ✅ Include it in context
    })


@router.post("/rooms/create")
def create_room_post(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    # 💬 Check for existing room name
    existing = db.query(models.GameRoom).filter(models.GameRoom.name == name).first()
    if existing:
        return templates.TemplateResponse("create-room.html", {
            "request": request,
            "user": current_user,
            "error": "❌ Room name already exists."
        })

    # 💰 Check coin balance
    if current_user.coins < 20:
        return templates.TemplateResponse("create-room.html", {
            "request": request,
            "user": current_user,
            "error": "⚠️ You need at least 20 coins to create a room."
        })

    # 💸 Deduct coins
    current_user.coins -= 20

    # ✅ Create room
    room = models.GameRoom(
        name=name,
        description=description,
        created_by=current_user.id
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return RedirectResponse(f"/game-room/{room.id}", status_code=303)

@router.post("/rooms/create")
def create_room_post(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    unread_notif_count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.read == False
    ).count()

    existing = db.query(models.GameRoom).filter(models.GameRoom.name == name).first()
    if existing:
        return templates.TemplateResponse("create-room.html", {
            "request": request,
            "user": current_user,
            "unread_notif_count": unread_notif_count,
            "error": "❌ Room name already exists."
        })

    if current_user.coins < 20:
        return templates.TemplateResponse("create-room.html", {
            "request": request,
            "user": current_user,
            "unread_notif_count": unread_notif_count,
            "error": "⚠️ You need at least 20 coins to create a room."
        })

    # Deduct coins and create room
    current_user.coins -= 20
    room = models.GameRoom(
        name=name,
        description=description,
        created_by=current_user.id
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return RedirectResponse(f"/game-room/{room.id}", status_code=303)


# ✅ List Rooms
@router.get("/game-room")
def list_rooms(
    request: Request,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    rooms = db.query(models.GameRoom).all()

    # IDs of rooms the user has already joined
    joined_rooms = db.query(models.GameRoomUser).filter_by(user_id=user.id).all()
    user_joined_room_ids = [r.room_id for r in joined_rooms]

    # IDs of rooms where the user has sent join requests
    pending = db.query(models.RoomJoinRequest).filter_by(user_id=user.id, status="pending").all()
    pending_requests = [r.room_id for r in pending]

    return templates.TemplateResponse("game_room_list.html", {
    "request": request,
    "user": user,
    "rooms": rooms,
    "user_joined_room_ids": user_joined_room_ids,
    "pending_requests": pending_requests
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
@router.get("/game-chat/{room_id}/chat")
def get_chat_messages(
    request: Request,
    room_id: int,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Game room not found")
    messages = db.query(models.Message).filter(models.Message.room_id == room_id).order_by(models.Message.timestamp.asc()).all()
    return templates.TemplateResponse("chat_room.html", {
        "request": request,
        "user": user,
        "room": room,
        "messages": messages
        
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

@router.get("/games/chess", response_class=HTMLResponse)
def chess_game(request: Request):
    return templates.TemplateResponse("chess.html", {"request": request})

@router.get("/games/ludo", response_class=HTMLResponse)
def ludo_game(request: Request):
    return templates.TemplateResponse("ludo.html", {"request": request})

@router.get("/games/snake-ladder", response_class=HTMLResponse)
def snake_ladder_game(request: Request):
    return templates.TemplateResponse("snake_ladder.html", {"request": request})

@router.get("/games/carrom", response_class=HTMLResponse)
def carrom_game(request: Request):
    return templates.TemplateResponse("carrom.html", {"request": request})


# routers/contact.py





@router.get("/contact")
def contact_form(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@router.post("/contact")
def submit_contact(
    request: Request,
    type: str = Form(...),
    email: str = Form(""),
    message: str = Form(...),
    db: Session = Depends(get_db)
):
    contact = models.ContactMessage(type=type, email=email, message=message)
    db.add(contact)
    db.commit()
    return RedirectResponse("/contact", status_code=status.HTTP_302_FOUND)

@router.post("/game-chat/{room_id}/kick/{user_id}")
def kick_user_from_room(
    room_id: int,
    user_id: int,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room owner can kick users")

    participant = db.query(models.GameRoomUser).filter_by(user_id=user_id, room_id=room_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="User is not in the room")

    # Send system message before removal
    system_message = models.Message(
        room_id=room_id,
        sender_id=None,  # None or a dedicated "system user" ID
        content=f"User {participant.user.full_name} was kicked out by the room owner.",
        timestamp=datetime.utcnow()
    )
    db.add(system_message)

    # Optionally: notify the user directly if you have user-specific inbox or alerts
    # (e.g., insert to Notification table)

    db.delete(participant)
    db.commit()

    return RedirectResponse(url=f"/game-chat/{room_id}/chat", status_code=303)


@router.post("/game-chat/{room_id}/invite")
def invite_user_to_room(
    room_id: int,
    invited_user_id: int = Form(...),
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can invite users")

    # Check if already in room
    exists = db.query(models.GameRoomUser).filter_by(user_id=invited_user_id, room_id=room_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="User already in room")

    new_participant = models.GameRoomUser(user_id=invited_user_id, room_id=room_id)
    db.add(new_participant)
    db.commit()

    return RedirectResponse(url=f"/game-chat/{room_id}/chat", status_code=303)

@router.post("/game-room/{room_id}/join-request")
def send_join_request(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    # Check if already a member
    existing = db.query(models.GameRoomUser).filter_by(room_id=room_id, user_id=current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")

    # Check if request already exists
    request_exists = db.query(models.RoomJoinRequest).filter_by(
        room_id=room_id,
        user_id=current_user.id,
        status="pending"
    ).first()
    if request_exists:
        raise HTTPException(status_code=400, detail="Request already sent")

    join_request = models.RoomJoinRequest(
        room_id=room_id,
        user_id=current_user.id
    )
    db.add(join_request)
    db.commit()
    return RedirectResponse(url="/game-room", status_code=303)





@router.get("/game-room/{room_id}/requests", response_class=HTMLResponse)
def view_join_requests(
    room_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    # Make sure room exists and is owned by the current user
    room = db.query(models.GameRoom).filter_by(id=room_id, created_by=current_user.id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found or not owned by you")

    # Get all pending requests for the room
    join_requests = (
        db.query(models.RoomJoinRequest)
        .filter_by(room_id=room_id, status="pending")
        .all()
    )

    return templates.TemplateResponse("room_requests.html", {
        "request": request,
        "room": room,
        "join_requests": join_requests,
        "user": current_user
    })




@router.post("/game-room/{room_id}/requests/{request_id}/accept")
def accept_join_request(room_id: int, request_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user_from_cookie)):
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    join_request = db.query(models.RoomJoinRequest).filter(models.RoomJoinRequest.id == request_id).first()

    if not room or room.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if join_request and join_request.status == "pending":
        join_request.status = "accepted"
        db.add(models.GameRoomUser(room_id=room_id, user_id=join_request.user_id))
        db.commit()

    return RedirectResponse(url=f"/game-room/{room_id}/requests", status_code=302)



@router.post("/game-room/{room_id}/requests/{request_id}/reject")
def reject_join_request(room_id: int, request_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user_from_cookie)):
    room = db.query(models.GameRoom).filter(models.GameRoom.id == room_id).first()
    join_request = db.query(models.RoomJoinRequest).filter(models.RoomJoinRequest.id == request_id).first()

    if not room or room.created_by != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if join_request and join_request.status == "pending":
        join_request.status = "rejected"
        db.commit()

    return RedirectResponse(url=f"/game-room/{room_id}/requests", status_code=302)


@router.get("/game-chat/{room_id}/chat")
def get_chat_messages(
    request: Request,
    room_id: int,
    user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    room = db.query(models.GameRoom).filter_by(id=room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Access only if creator or accepted member
    is_creator = room.created_by == user.id
    is_member = db.query(models.GameRoomUser).filter_by(room_id=room_id, user_id=user.id).first()

    if not is_creator and not is_member:
        raise HTTPException(status_code=403, detail="You are not a member of this room.")

    messages = db.query(models.Message).filter_by(room_id=room_id).all()
    return templates.TemplateResponse("chat_room.html", {
        "request": request,
        "user": user,
        "room": room,
        "messages": messages
    })


@router.post("/game-room/{room_id}/delete")
def delete_game_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    # ✅ Find the room
    room = db.query(models.GameRoom).filter_by(id=room_id).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the room owner can delete this room")

    # ✅ Delete related ludo_games entries
    db.query(models.LudoGame).filter_by(room_id=room_id).delete()

    # ✅ Delete messages, users, requests
    db.query(models.Message).filter_by(room_id=room_id).delete()
    db.query(models.GameRoomUser).filter_by(room_id=room_id).delete()
    db.query(models.RoomJoinRequest).filter_by(room_id=room_id).delete()

    # ✅ Now delete the game room itself
    db.delete(room)
    db.commit()

    return RedirectResponse(url="/game-room", status_code=303)
