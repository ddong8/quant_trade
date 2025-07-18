# backend/app/schemas/token.py

from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    exp: Optional[int] = None
    sub: Optional[str] = None