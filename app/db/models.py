from sqlalchemy import JSON, Column, Date, Integer, String, ForeignKey, Boolean, DateTime, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from sqlalchemy.ext.associationproxy import association_proxy

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)  # Required for password reset
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    coins = Column(Integer, default=0)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    high_score = Column(Integer, default=0)    
    last_daily_claim = Column(DateTime, nullable=True)
    user_code = Column(String, unique=True, index=True)
    buddy_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    buddy = relationship("User", remote_side=[id], uselist=False)
    banned = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)  # 👈 NEW
    last_active = Column(DateTime, default=datetime.utcnow)  # 👈 NEW
    # Relationships
    rooms = relationship("GameRoom", back_populates="creator")
    guilds_created = relationship(
    "Guild",
    back_populates="creator",
    foreign_keys="[Guild.created_by]"
)
    # For many-to-many guilds
    guild_memberships = relationship("GuildMember", back_populates="user")
    guilds = association_proxy("guild_memberships", "guild")

    

    # For direct 1 guild via FK
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=True)
    guild = relationship("Guild", back_populates="users_in_guild", foreign_keys=[guild_id])

    private_messages = relationship("Message", back_populates="sender")
    guild_messages = relationship("GuildMessage", back_populates="user", cascade="all, delete")
    is_developer = Column(Boolean, default=False)
   
    reports_received = relationship("UserReport", back_populates="reported_user", foreign_keys='UserReport.reported_user_id')
    reports_made = relationship("UserReport", back_populates="reporter_user", foreign_keys='UserReport.reporter_user_id')
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
  


class UserReport(Base):
    __tablename__ = "user_reports"

    id = Column(Integer, primary_key=True, index=True)
    reported_user_id = Column(Integer, ForeignKey("users.id"))
    reporter_user_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    reported_user = relationship("User", foreign_keys=[reported_user_id])
    reporter_user = relationship("User", foreign_keys=[reporter_user_id])


class BuddyRequest(Base):
    __tablename__ = "buddy_requests"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending")  # pending / accepted / rejected
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_buddy_requests")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_buddy_requests")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)  # report, review, suggestion, etc.
    email = Column(String(255), nullable=True)  # optional email
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    

class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True)
    blocker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blocked_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    __table_args__ = (UniqueConstraint('blocker_id', 'blocked_id', name='unique_block_pair'),)

    blocker = relationship("User", foreign_keys=[blocker_id])
    blocked = relationship("User", foreign_keys=[blocked_id])



class GameRoom(Base):
    __tablename__ = "game_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    creator = relationship("User", back_populates="rooms")
    messages = relationship("Message", back_populates="room")
    participants = relationship("GameRoomUser", back_populates="room", cascade="all, delete-orphan")    
    ludo_games = relationship("LudoGame", back_populates="room", cascade="all, delete", passive_deletes=True)



class GameRoomUser(Base):
    __tablename__ = "game_room_users"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("game_rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    joined_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("GameRoom", back_populates="participants")
    user = relationship("User")


class RoomJoinRequest(Base):
    __tablename__ = "room_join_requests"

    id = Column(Integer, primary_key=True)
    room_id = Column(
        Integer,
        ForeignKey("game_rooms.id", ondelete="CASCADE"),  # <-- this is critical
        nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")
    timestamp = Column(DateTime, default=datetime.utcnow)

    room = relationship("GameRoom", passive_deletes=True)
    user = relationship("User")


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
    creator = relationship(
    "User",
    back_populates="guilds_created",
    foreign_keys=[created_by]
)

    messages = relationship("GuildMessage", back_populates="guild", cascade="all, delete")
    creator = relationship(
        "User",
        back_populates="guilds_created",
        foreign_keys=[created_by]
    )
    users_in_guild = relationship("User", back_populates="guild", foreign_keys=[User.guild_id])
     # Avoid naming conflict — change `members` to `member_links`
    member_links = relationship("GuildMember", back_populates="guild", cascade="all, delete")
    members = association_proxy("member_links", "user")

    
class GuildMember(Base):
    __tablename__ = "guild_members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    guild_id = Column(Integer, ForeignKey("guilds.id"))
    joined_at = Column(DateTime, default=datetime.utcnow)
    role = Column(String, default="Member")  
    online = Column(Boolean, default=False)

    user = relationship("User", back_populates="guild_memberships")
    guild = relationship("Guild", back_populates="member_links")  



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
    read = Column(Boolean, default=False)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String, nullable=False)
    read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
     # Optional additions for linking to context
    type = Column(String, default="info")  # e.g., "message"
    related_user_id = Column(Integer, nullable=True) 
    user = relationship("User", back_populates="notifications")


class LudoGame(Base):
    __tablename__ = "ludo_games"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("game_rooms.id"), unique=True)
    current_turn = Column(Integer, ForeignKey("users.id"))  # whose turn is it
    state = Column(JSON, default={})  # JSON blob for game state
    started = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("GameRoom")
    current_player = relationship("User")
    room_id = Column(Integer, ForeignKey("game_rooms.id", ondelete="CASCADE"))
    room = relationship("GameRoom", back_populates="ludo_games")
