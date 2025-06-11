import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("postgresql://piano_master:CrgApfmcqwDpFiWWZyC5MsREH9GS8STv@dpg-d141lmmmcj7s738inc8g-a.oregon-postgres.render.com/piano_db_xesr")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")