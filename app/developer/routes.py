from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.models import User, UserReport
from app.core.deps import get_db, get_current_user_from_cookie
from sqlalchemy.orm import joinedload

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/developer/reports", response_class=HTMLResponse)
def view_reports(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_cookie)):
    if not current_user.is_developer:
        raise HTTPException(status_code=403, detail="Access forbidden")

    reports = db.query(UserReport).options(joinedload(UserReport.reported_user)).all()

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "reports": reports
    })

@router.post("/developer/ban-user")
def ban_user(user_id: int = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_cookie)):
    if not current_user.is_developer:
        raise HTTPException(status_code=403, detail="Access forbidden")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.banned = True
    db.commit()

    return RedirectResponse(url="/developer/reports", status_code=303)

@router.post("/developer/ban")
def ban_user(user_id: int = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_cookie)):
    if current_user.username != "developer":
        raise HTTPException(status_code=403, detail="Access forbidden")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_banned = True
    db.commit()
    return RedirectResponse("/developer/reports", status_code=302)

@router.post("/developer/toggle-ban")
def toggle_ban_user(
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    if not current_user.is_developer:
        raise HTTPException(status_code=403, detail="Access forbidden")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.banned = not user.banned  # Toggle status
    db.commit()

    return RedirectResponse(url="/developer/reports", status_code=303)
