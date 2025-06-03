# seed_friendship.py
from app.db.models import Friendship
from app.core.database import SessionLocal

db = SessionLocal()
logged_in_user_id = 2
friend_id = 1

# Create mutual accepted friendship if it doesn't exist
if not db.query(Friendship).filter_by(
    user_id=logged_in_user_id, friend_id=friend_id, accepted=True
).first():
    db.add(Friendship(
        user_id=logged_in_user_id,
        friend_id=friend_id,
        accepted=True
    ))
if not db.query(Friendship).filter_by(
    user_id=friend_id, friend_id=logged_in_user_id, accepted=True
).first():
    db.add(Friendship(
        user_id=friend_id,
        friend_id=logged_in_user_id,
        accepted=True
    ))
db.commit()
db.close()
print("⭐ Seeded friendship between", logged_in_user_id, "and", friend_id)
