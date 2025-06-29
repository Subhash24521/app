from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.deps import get_current_user_from_cookie
from app.core.database import SessionLocal
from datetime import datetime
class UpdateLastActiveMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        db = SessionLocal()
        try:
            # Remove 'await' if get_current_user_from_cookie is a sync function
            user = get_current_user_from_cookie(request, db)
            if user:
                user.last_active = datetime.utcnow()
                db.commit()
        except Exception as e:
            print("Error updating last_active:", e)
        finally:
            db.close()
        
        response = await call_next(request)
        return response
