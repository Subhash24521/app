from datetime import datetime
from urllib import request
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER

from app.core.database import get_db
from app.core.deps import get_current_user_from_cookie
from app.db import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/guilds/create", response_class=HTMLResponse)
def show_create_guild_form(
    request: Request,
    user: models.User = Depends(get_current_user_from_cookie),
):
    return templates.TemplateResponse("create_guild.html", {"request": request, "user": user})


@router.post("/guilds/create")
def create_guild_post(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    existing = db.query(models.Guild).filter(models.Guild.name == name).first()
    if existing:
        return templates.TemplateResponse("create_guild.html", {
            "request": request,
            "user": current_user,
            "error": "Guild name already exists",
        })

    guild = models.Guild(name=name, description=description, created_by=current_user.id)
    db.add(guild)
    db.commit()
    db.refresh(guild)

    # Add founder
    founder_membership = models.GuildMember(user_id=current_user.id, guild_id=guild.id, role="Founder")
    db.add(founder_membership)
    db.commit()

    return RedirectResponse(f"/guilds/{guild.id}", status_code=HTTP_303_SEE_OTHER)


@router.get("/guilds", response_class=HTMLResponse)
def available_guilds(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_from_cookie),
):
    guilds = db.query(models.Guild).all()
    return templates.TemplateResponse("available_guilds.html", {"request": request, "guilds": guilds, "user": user})


@router.get("/guilds/{guild_id}", response_class=HTMLResponse)
def guild_detail(
    request: Request,
    guild_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_from_cookie),
):
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    membership = db.query(models.GuildMember).filter_by(user_id=user.id, guild_id=guild_id).first()

    if not membership:
        return templates.TemplateResponse("guild_join.html", {
            "request": request,
            "guild": guild,
            "user": user,
        })

    user_role = membership.role
    members = (
        db.query(models.GuildMember)
        .filter(models.GuildMember.guild_id == guild_id)
        .join(models.User, models.User.id == models.GuildMember.user_id)
        .all()
    )
    messages = (
        db.query(models.GuildMessage)
        .filter(models.GuildMessage.guild_id == guild_id)
        .order_by(models.GuildMessage.timestamp.asc())
        .all()
    )

    join_requests = []
    if user.id == guild.created_by:
        join_requests = (
            db.query(models.GuildJoinRequest)
            .filter(models.GuildJoinRequest.guild_id == guild_id, models.GuildJoinRequest.status == "pending")
            .all()
        )

        

    return templates.TemplateResponse("guild_detail.html", {
        "request": request,
        "guild": guild,
        "current_user": user,
        "is_member": True,
        "members": members,
        "messages": messages,
        "user_role": user_role,
        "join_requests": join_requests,
    })


# 🚫 Direct Join is disabled — force join via request

@router.get("/guilds/{guild_id}/join", response_class=HTMLResponse)
async def join_guild_get(request: Request, guild_id: int):
    return templates.TemplateResponse("join_blocked.html", {"request": request, "guild_id": guild_id})

@router.post("/guilds/{guild_id}/join")
async def join_guild_post_blocked(request: Request, guild_id: int):
    return templates.TemplateResponse("join_blocked.html", {"request": request, "guild_id": guild_id})


# Request to join a guild
@router.post("/guilds/{guild_id}/request_join")
def request_to_join_guild(
    guild_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_from_cookie),
):
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    existing_member = db.query(models.GuildMember).filter_by(user_id=user.id, guild_id=guild_id).first()
    if existing_member:
        return RedirectResponse(f"/guilds/{guild_id}", status_code=HTTP_303_SEE_OTHER)

    existing_request = (
        db.query(models.GuildJoinRequest)
        .filter_by(user_id=user.id, guild_id=guild_id, status="pending")
        .first()
    )
    if existing_request:
        raise HTTPException(status_code=400, detail="Join request already sent")

    join_request = models.GuildJoinRequest(
        guild_id=guild_id,
        user_id=user.id,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(join_request)
    db.commit()

    return RedirectResponse(f"/guilds/{guild_id}", status_code=HTTP_303_SEE_OTHER)

@router.post("/guilds/{guild_id}/leave")
def leave_guild(
    guild_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_from_cookie),
):
    membership = db.query(models.GuildMember).filter_by(user_id=user.id, guild_id=guild_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member")
    if membership.role == "Founder":
        raise HTTPException(status_code=400, detail="Founder cannot leave the guild")

    db.delete(membership)
    db.commit()
    return RedirectResponse("/guilds", status_code=HTTP_303_SEE_OTHER)


@router.post("/guilds/{guild_id}/messages", response_class=RedirectResponse)
def post_chat_message(
    request: Request,
    guild_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    membership = db.query(models.GuildMember).filter_by(user_id=current_user.id, guild_id=guild_id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="You must be a member to post messages")

    new_message = models.GuildMessage(
        guild_id=guild_id,
        user_id=current_user.id,
        content=content,
        timestamp=datetime.utcnow(),
    )
    db.add(new_message)
    db.commit()
    return RedirectResponse(url=f"/guilds/{guild_id}", status_code=HTTP_303_SEE_OTHER)


@router.post("/guilds/{guild_id}/edit_description")
def edit_guild_description(
    guild_id: int,
    description: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_from_cookie),
):
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    membership = db.query(models.GuildMember).filter_by(user_id=user.id, guild_id=guild_id).first()
    if not membership or membership.role != "Founder":
        raise HTTPException(status_code=403, detail="Only the founder can edit the description")

    guild.description = description
    db.commit()
    return RedirectResponse(url=f"/guilds/{guild_id}", status_code=HTTP_303_SEE_OTHER)





@router.get("/guilds/{guild_id}/requests", response_class=HTMLResponse)
def view_join_requests(
    guild_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    # 1. Fetch the actual Guild instance
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    # 2. Verify the current user is the founder of this guild
    membership = (
        db.query(models.GuildMember)
        .filter_by(user_id=current_user.id, guild_id=guild_id)
        .first()
    )
    if not membership or membership.role != "Founder":
        raise HTTPException(status_code=403, detail="Only the founder can view join requests")

    # 3. Fetch pending join requests joined to the User table
    pending_requests = (
        db.query(models.GuildJoinRequest, models.User)
        .join(models.User, models.User.id == models.GuildJoinRequest.user_id)
        .filter(
            models.GuildJoinRequest.guild_id == guild_id,
            models.GuildJoinRequest.status == "pending"
        )
        .all()
    )
    # pending_requests is a list of (GuildJoinRequest, User) tuples

    # 4. Build a simple list of dicts for the template
    request_data = [
        {
            "request_id": req.id,
            "user_id": usr.id,
            "username": usr.username
        }
        for req, usr in pending_requests
    ]

    return templates.TemplateResponse("guild_requests.html", {
        "request": request,
        "guild": guild,
        "current_user": current_user,
        "requests": request_data,
    })






@router.post("/guilds/{guild_id}/disband")
def disband_guild(
    guild_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_from_cookie),
):
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    if guild.created_by != user.id:
        raise HTTPException(status_code=403, detail="Only the founder can disband the guild")

    # Delete related data manually
    db.query(models.GuildJoinRequest).filter_by(guild_id=guild_id).delete()
    db.query(models.GuildMember).filter_by(guild_id=guild_id).delete()
    db.query(models.GuildMessage).filter_by(guild_id=guild_id).delete()

    db.delete(guild)
    db.commit()

    return RedirectResponse(url="/guilds", status_code=HTTP_303_SEE_OTHER)



# 1. Promote / Demote endpoint (Founder only)
@router.post("/guilds/{guild_id}/promote/{member_id}")
def promote_guild_member(
    guild_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    # Fetch guild and verify existence
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    # Only founder can promote/demote
    if guild.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the founder can promote/demote members")

    # Fetch the GuildMember row for the target user
    membership = (
        db.query(models.GuildMember)
        .filter_by(user_id=member_id, guild_id=guild_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this guild")

    # Founder cannot demote themself
    if membership.user_id == guild.created_by:
        raise HTTPException(status_code=400, detail="Creator cannot be demoted")

    # Toggle between Member ⇄ Manager
    if membership.role == "Member":
        membership.role = "Manager"
    elif membership.role == "Manager":
        membership.role = "Member"
    else:
        # Should never happen for “Founder,” but just in case:
        raise HTTPException(status_code=400, detail="Cannot change this user’s role")

    db.commit()
    return RedirectResponse(url=f"/guilds/{guild_id}", status_code=HTTP_303_SEE_OTHER)


# 2. Approve join request (Founder or Manager)
@router.post("/guilds/{guild_id}/requests/{user_id}/approve")
def approve_request(
    guild_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    # Fetch guild
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    # Check caller’s membership and role
    caller_membership = (
        db.query(models.GuildMember)
        .filter_by(user_id=current_user.id, guild_id=guild_id)
        .first()
    )
    if not caller_membership or caller_membership.role not in ("Founder", "Manager"):
        raise HTTPException(status_code=403, detail="Only a Founder or Manager can approve requests")

    # Approve logic
    pending = (
        db.query(models.GuildJoinRequest)
        .filter_by(guild_id=guild_id, user_id=user_id, status="pending")
        .first()
    )
    if not pending:
        raise HTTPException(status_code=404, detail="Join request not found")

    # If member limit is a concern, enforce it here
    member_count = db.query(models.GuildMember).filter_by(guild_id=guild_id).count()
    if member_count >= 50:
        raise HTTPException(status_code=400, detail="Guild member limit reached")

    # Mark request approved and create membership
    pending.status = "approved"
    new_member = models.GuildMember(user_id=user_id, guild_id=guild_id, role="Member")
    db.add(new_member)
    db.commit()

    return RedirectResponse(url=f"/guilds/{guild_id}", status_code=HTTP_303_SEE_OTHER)


# 3. Reject join request (Founder or Manager)
@router.post("/guilds/{guild_id}/requests/{user_id}/reject")
def reject_request(
    guild_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    # Fetch guild
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    # Check caller’s membership and role
    caller_membership = (
        db.query(models.GuildMember)
        .filter_by(user_id=current_user.id, guild_id=guild_id)
        .first()
    )
    if not caller_membership or caller_membership.role not in ("Founder", "Manager"):
        raise HTTPException(status_code=403, detail="Only a Founder or Manager can reject requests")

    # Reject logic
    pending = (
        db.query(models.GuildJoinRequest)
        .filter_by(guild_id=guild_id, user_id=user_id, status="pending")
        .first()
    )
    if not pending:
        raise HTTPException(status_code=404, detail="Join request not found")

    pending.status = "rejected"
    db.commit()

    return RedirectResponse(url=f"/guilds/{guild_id}", status_code=HTTP_303_SEE_OTHER)


# 4. Kick guild member (Founder or Manager, but cannot kick Founder or other Managers if caller is Manager)
@router.post("/guilds/{guild_id}/kick/{member_id}")
def kick_guild_member(
    guild_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    # Fetch guild and verify existence
    guild = db.query(models.Guild).filter(models.Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    # Fetch caller’s membership + role
    caller_membership = (
        db.query(models.GuildMember)
        .filter_by(user_id=current_user.id, guild_id=guild_id)
        .first()
    )
    if not caller_membership or caller_membership.role not in ("Founder", "Manager"):
        raise HTTPException(status_code=403, detail="Only a Founder or Manager can kick members")

    # Fetch the target membership
    target_membership = (
        db.query(models.GuildMember)
        .filter_by(user_id=member_id, guild_id=guild_id)
        .first()
    )
    if not target_membership:
        raise HTTPException(status_code=404, detail="User is not a member of this guild")

    # Prevent kicking the founder
    if target_membership.role == "Founder":
        raise HTTPException(status_code=400, detail="Founder cannot be kicked")

    # If caller is Manager, they cannot kick other Managers
    if caller_membership.role == "Manager" and target_membership.role == "Manager":
        raise HTTPException(status_code=403, detail="Managers cannot kick fellow Managers")

    # All checks passed → delete membership
    db.delete(target_membership)
    db.commit()
    return RedirectResponse(url=f"/guilds/{guild_id}", status_code=HTTP_303_SEE_OTHER)