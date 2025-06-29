from app.core.database import SessionLocal
from app.db.models import User
from app.core.security import get_password_hash

db = SessionLocal()

dev = User(
    username="developersubhash",
    email="developernenogame@gmail.com",
    hashed_password=get_password_hash("subbudev245"),
    is_developer=True,
)
db.add(dev)
db.commit()
db.close()
print("✅ Developer created")
