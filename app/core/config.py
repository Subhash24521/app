import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("postgresql+psycopg2://postgres:2452@localhost:2245/chess_appdb")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  
