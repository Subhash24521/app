from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    rooms = relationship("GameRoom", back_populates="creator")
    messages = relationship("Message", back_populates="sender")
    guilds_created = relationship("Guild", back_populates="creator")
    guild_memberships = relationship("GuildMember", back_populates="user")
    messages = relationship("GuildMessage", back_populates="user", cascade="all, delete")



    


class GameRoom(Base):
    __tablename__ = "game_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="rooms")
    messages = relationship("Message", back_populates="room")

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey('game_rooms.id'))
    sender_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    room = relationship("GameRoom", back_populates="messages")
    sender = relationship("User")

class Guild(Base):
    __tablename__ = "guilds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="guilds_created")
    members = relationship("GuildMember", back_populates="guild", cascade="all, delete")
    messages = relationship("GuildMessage", back_populates="guild", cascade="all, delete")



class GuildMember(Base):
    __tablename__ = "guild_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    guild_id = Column(Integer, ForeignKey("guilds.id"))
    joined_at = Column(DateTime, default=datetime.utcnow)
    role = Column(String, default="Member")  # Founder, Manager, Officer, Member
    online = Column(Boolean, default=False)

    user = relationship("User", back_populates="guild_memberships")
    guild = relationship("Guild", back_populates="members")



class GuildMessage(Base):
    __tablename__ = "guild_messages"

    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    guild = relationship("Guild", back_populates="messages")
    user = relationship("User")  

class GuildJoinRequest(Base):
     __tablename__ = "guild_join_requests"

     id = Column(Integer, primary_key=True, index=True)  # ✅ Primary key
     guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
     status = Column(String, default="pending")  # e.g., pending, approved, rejected
     created_at = Column(DateTime, default=datetime.utcnow)

    # Optional relationships
     user = relationship("User")
     guild = relationship("Guild")

