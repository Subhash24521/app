import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.models import User, Friendship, PrivateMessage
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
        "send_message.html",
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
    """
    Handle form submission. Verify that receiver_id is a valid friend,
    and that content is not empty. Otherwise re-render with error.
    """
    sender_id = current_user.id

    # 1) Re-fetch accepted friends so we can re-display the dropdown if needed
    friends = (
        db.query(User)
        .join(Friendship, Friendship.friend_id == User.id)
        .filter(Friendship.user_id == sender_id, Friendship.accepted == True)
        .all()
    )

    # 2) Verify receiver is actually in friends
    if not any(f.id == receiver_id for f in friends):
        return templates.TemplateResponse(
            "send_message.html",
            {
                "request": request,
                "users": friends,
                "receiver_id": None,
                "error": "You can only send messages to your friends.",
            },
        )

    # 3) Ensure content is not blank
    content_clean = content.strip()
    if not content_clean:
        return templates.TemplateResponse(
            "send_message.html",
            {
                "request": request,
                "users": friends,
                "receiver_id": receiver_id,
                "error": "Message content cannot be empty.",
            },
        )

    # 4) Save new PrivateMessage
    message = PrivateMessage(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content_clean,
        timestamp=datetime.datetime.utcnow(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return RedirectResponse(
        url=f"/private-messages/{message.id}", status_code=status.HTTP_303_SEE_OTHER
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
    """
    Show a chat‐style interface:
      - Sidebar: all accepted friends of current_user
      - Main pane: conversation with ?friend_id= (if provided), otherwise a placeholder
    """
    # 1) Fetch all accepted friends for the sidebar
    friends = (
        db.query(User)
        .join(Friendship, Friendship.friend_id == User.id)
        .filter(Friendship.user_id == current_user.id, Friendship.accepted == True)
        .all()
    )

    selected_user = None
    messages = []

    # 2) If friend_id is given, ensure they are in current_user’s friend list
    if friend_id is not None:
        if not any(f.id == friend_id for f in friends):
            raise HTTPException(status_code=404, detail="Friend not found")

        selected_user = db.query(User).filter(User.id == friend_id).first()
        # 3) Load messages between current_user and selected_user (both directions)
        messages = (
            db.query(PrivateMessage)
            .filter(
                ((PrivateMessage.sender_id == current_user.id)
                  & (PrivateMessage.receiver_id == friend_id))
                | ((PrivateMessage.sender_id == friend_id)
                  & (PrivateMessage.receiver_id == current_user.id))
            )
            .order_by(PrivateMessage.timestamp.asc())
            .all()
        )

    return templates.TemplateResponse(
        "list_messages.html",
        {
            "request": request,
            "users": friends,
            "selected_user": selected_user,
            "messages": messages,
            "current_user": current_user,
        },
    )


@router.post("/private-messages/chat/{friend_id}")
def post_message_to_friend(
    friend_id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie),
):
    """
    Handle sending a new chat message to `/private-messages/?friend_id=<X>`.
    """
    sender_id = current_user.id

    # Verify they are still friends
    if not are_friends(db, sender_id, friend_id):
        raise HTTPException(status_code=403, detail="Not friends with that user")

    # Save the new message
    new_msg = PrivateMessage(
        sender_id=sender_id,
        receiver_id=friend_id,
        content=content.strip(),
        timestamp=datetime.datetime.utcnow(),
    )
    db.add(new_msg)
    db.commit()

    # Redirect back to GET /private-messages/?friend_id=<X>
    return RedirectResponse(
        url=f"/private-messages/?friend_id={friend_id}", status_code=status.HTTP_303_SEE_OTHER
    )
