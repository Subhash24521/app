from datetime import datetime
from pydantic import BaseModel

class GuildCreate(BaseModel):
    name: str
    description: str | None = None

class GuildOut(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: int

    class Config:
        orm_mode = True


class GuildMessageBase(BaseModel):
    content: str

class GuildMessageCreate(GuildMessageBase):
    pass

class GuildMessageRead(GuildMessageBase):
    id: int
    guild_id: int
    user_id: int
    timestamp: datetime

    class Config:
        orm_mode = True