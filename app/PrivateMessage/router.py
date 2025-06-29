import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.utils import is_blocked
from app.db.models import Notification, User, Friendship, PrivateMessage
from app.core.deps import get_current_user_from_cookie
from app.core.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def are_friends(db: Session, user_a: int, user_b: int) -> bool:
    """
    Return True if user_a → user_b friendship is accepted.
    """
    return (
        db.query(Friendship)
        .filter(
            Friendship.user_id == user_a,
            Friendship.friend_id == user_b,
            Friendship.accepted == True,
        )
        .first()
        is not None
    )


@router.get("/private-messages/send", response_class=HTMLResponse)
def send_message_form(
    request: Request,
    receiver_id: int = None,
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
):
    """
    Render the “Send Message” form. Dropdown shows only accepted friends.
    If ?receiver_id= was provided (and is actually a friend), preselect it.
    """
    # 1) Fetch all accepted friends of current_user
    friends = (
        db.query(User)
        .join(Friendship, Friendship.friend_id == User.id)
        .filter(Friendship.user_id == current_user.id, Friendship.accepted == True)
        .all()
    )

    # 2) If the query param receiver_id is not in that friends list, ignore it
    if receiver_id is not None and not any(f.id == receiver_id for f in friends):
        receiver_id = None

    return templates.TemplateResponse(
        "list_messages.html", 
        {
            "request": request,
            "users": friends,         # list of User objects
            "receiver_id": receiver_id,
            "error": None,
        },
    )

@router.post("/private-messages/send")
def send_message(
    request: Request,
    receiver_id: int = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    sender_id = current_user.id

    # Get friends of current user
    friends = (
        db.query(User)
        .join(Friendship, Friendship.friend_id == User.id)
        .filter(Friendship.user_id == sender_id, Friendship.accepted == True)
        .all()
    )

    # Check if the receiver is a valid friend
    if not any(f.id == receiver_id for f in friends):
        return templates.TemplateResponse(
            "list_messages.html", 
            {
                "request": request,
                "users": friends,
                "receiver_id": None,
                "error": "You can only send messages to your friends.",
            },
        )

    # Check block status
    if is_blocked(sender_id, receiver_id, db):
        return templates.TemplateResponse(
            "list_messages.html", 
            {
                "request": request,
                "users": friends,
                "receiver_id": receiver_id,
                "error": "Message blocked due to user restrictions.",
            },
        )

    content_clean = content.strip()
    if not content_clean:
        return templates.TemplateResponse(
            "list_messages.html",
            {
                "request": request,
                "users": friends,
                "receiver_id": receiver_id,
                "error": "Message content cannot be empty.",
            },
        )

    # ✅ Save the message with read=False
    message = PrivateMessage(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content_clean,
        timestamp=datetime.utcnow(),
        read=False  # 👈 Mark as unread initially
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # ✅ Create a notification (optional)
    notif = Notification(
        user_id=receiver_id,
        message=f"You have a new message from {current_user.username}",
        timestamp=datetime.utcnow(),
    )
    db.add(notif)
    db.commit()

    return RedirectResponse(
        url=f"/private-messages/?friend_id={receiver_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )



@router.get("/private-messages/{message_id}", response_class=HTMLResponse)
def view_message(
    message_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    """
    View a single message’s details. Anyone can view if they are sender OR receiver.
    """
    message = db.query(PrivateMessage).filter(PrivateMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Ensure the logged-in user is either sender or receiver
    if message.sender_id != current_user.id and message.receiver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this message")

    # Ensure they are still friends
    if not are_friends(db, message.sender_id, message.receiver_id):
        raise HTTPException(status_code=403, detail="Users are no longer friends")

    # Fetch sender/receiver usernames
    sender = db.query(User).filter(User.id == message.sender_id).first()
    receiver = db.query(User).filter(User.id == message.receiver_id).first()

    return templates.TemplateResponse(
        "view_message.html",
        {
            "request": request,
            "message": {
                "sender": sender,
                "receiver": receiver,
                "content": message.content,
                "timestamp": message.timestamp.strftime("%b %d, %Y %H:%M UTC"),
            },
        },
    )

@router.get("/private-messages/", response_class=HTMLResponse)
def list_messages(
    request: Request,
    friend_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    friends = (
        db.query(User)
        .join(Friendship, Friendship.friend_id == User.id)
        .filter(Friendship.user_id == current_user.id, Friendship.accepted == True)
        .all()
    )

    selected_user = None
    messages = []

    if friend_id is not None:
        if not any(f.id == friend_id for f in friends):
            raise HTTPException(status_code=404, detail="Friend not found")

        selected_user = db.query(User).filter(User.id == friend_id).first()

        db.query(PrivateMessage).filter(
            PrivateMessage.sender_id == friend_id,
            PrivateMessage.receiver_id == current_user.id,
            PrivateMessage.read == False
        ).update({PrivateMessage.read: True}, synchronize_session=False)
        db.commit()

        messages = (
            db.query(PrivateMessage)
            .filter(
                ((PrivateMessage.sender_id == current_user.id) & (PrivateMessage.receiver_id == friend_id))
                | ((PrivateMessage.sender_id == friend_id) & (PrivateMessage.receiver_id == current_user.id))
            )
            .order_by(PrivateMessage.timestamp.asc())
            .all()
        )

    # ✅ Count unread notifications
    unread_notif_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    ).count()

    return templates.TemplateResponse(
        "list_messages.html",
        {
            "request": request,
            "users": friends,
            "selected_user": selected_user,
            "messages": messages,
            "current_user": current_user,
            "unread_notif_count": unread_notif_count,  # 👈 Add this!
        },
    )



from datetime import datetime

@router.post("/private-messages/chat/{friend_id}")
def post_message_to_friend(
    friend_id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    sender_id = current_user.id

    # ✅ Check if they are still friends
    if not are_friends(db, sender_id, friend_id):
        raise HTTPException(status_code=403, detail="You are no longer friends with this user.")

    # ✅ Check if blocked (either direction)
    if is_blocked(sender_id, friend_id, db) or is_blocked(friend_id, sender_id, db):
        raise HTTPException(status_code=403, detail="Messaging is blocked due to user restrictions.")

    # ✅ Validate message content
    content_clean = content.strip()
    if not content_clean:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # ✅ Save the new message
    new_msg = PrivateMessage(
        sender_id=sender_id,
        receiver_id=friend_id,
        content=content_clean,
        timestamp=datetime.utcnow(),
        read=False
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    # ✅ Send notification
    notif = Notification(
        user_id=friend_id,
        message=f"You have a new message from {current_user.username}",
        timestamp=datetime.utcnow(),
        type="message",
        related_user_id=sender_id
    )
    db.add(notif)
    db.commit()

    # ✅ Redirect to chat view
    return RedirectResponse(
        url=f"/private-messages/?friend_id={friend_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/notifications/", response_class=HTMLResponse)
def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.timestamp.desc()).all()

    # Mark unread notifications as read
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    ).update({Notification.read: True})
    db.commit()

    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "notifications": notifications,
        "marked_read": request.query_params.get("marked_read") == "true"
    })


@router.post("/notifications/mark-read")
def mark_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read == False
    ).update({Notification.read: True})
    db.commit()
    
    # Redirect with query parameter
    return RedirectResponse("/notifications/?marked_read=true", status_code=status.HTTP_303_SEE_OTHER)


