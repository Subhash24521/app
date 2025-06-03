import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.auth.routes import router as auth_router
from app.games.routes import router as game_router
from app.chat.routes import router as chat_router
from app.guilds.router import router as guilds_router
from app.friendship.router import router as friends_router
from app.PrivateMessage.router import router as privatemessage_router
from app.db import models
from app.core.database import engine

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


models.Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(game_router)
app.include_router(chat_router)
app.include_router(guilds_router)
app.include_router(privatemessage_router)
app.include_router(friends_router, prefix="/friends", tags=["friends"])
