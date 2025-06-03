from sqlalchemy import Column, Date, Integer, String, ForeignKey, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    bio = Column(String)
    avatar_url = Column(String)
    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    coins = Column(Integer, default=0)
    last_login = Column(DateTime, default=None)
    is_admin = Column(Boolean, nullable=False, default=False)
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
    join_requests = relationship("GuildJoinRequest", cascade="all, delete-orphan", back_populates="guild")
    creator = relationship("User", back_populates="guilds_created")
    members = relationship("GuildMember", back_populates="guild", cascade="all, delete")
    messages = relationship("GuildMessage", back_populates="guild", cascade="all, delete")



class GuildMember(Base):
    __tablename__ = "guild_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    guild_id = Column(Integer, ForeignKey("guilds.id"))
    joined_at = Column(DateTime, default=datetime.utcnow)
    role = Column(String, default="Member")  
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

     id = Column(Integer, primary_key=True, index=True)  
     guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
     status = Column(String, default="pending") 
     created_at = Column(DateTime, default=datetime.utcnow)

  
     user = relationship("User") 
     guild = relationship("Guild", back_populates="join_requests")

class Friendship(Base):
    __tablename__ = "friendships"
   
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    friend_id = Column(Integer, ForeignKey("users.id"))
    accepted = Column(Boolean, default=False)  

    user = relationship("User", foreign_keys=[user_id])
    friend = relationship("User", foreign_keys=[friend_id])

class PrivateMessage(Base):
    __tablename__ = "private_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

