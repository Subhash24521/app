from pydantic import BaseModel

class Settings(BaseModel):

  SECRET_KEY = "your-secret-key"
  ALGORITHM = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
