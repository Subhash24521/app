# app/auth/config.py
from typing import ClassVar
from pydantic import BaseModel

class Settings(BaseModel):
    SECRET_KEY: ClassVar[str] = "your-secret-key"
    ALGORITHM: ClassVar[str] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: ClassVar[int] = 60 * 24 * 7



SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7