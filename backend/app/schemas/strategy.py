from pydantic import BaseModel
from typing import Optional

# Schema for receiving script content from the user
class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    script_content: str

# Base schema for database and API responses
class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    script_path: str

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    script_content: Optional[str] = None
    status: Optional[str] = None

# Schema for data returned from the DB
class StrategyInDB(StrategyBase):
    id: int
    status: str
    is_active: bool

    class Config:
        from_attributes = True

# Schema for API responses
class Strategy(StrategyInDB):
    pass
