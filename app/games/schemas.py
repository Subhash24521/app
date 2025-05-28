# schemas.py
from pydantic import BaseModel

class RoomCreate(BaseModel):
    name: str
    description: str | None = None

class RoomOut(BaseModel):
    id: int
    name: str
    description: str | None


class Config:
    from_attributes = True
