from pydantic import BaseModel
from typing import Optional

class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    script_path: str

class StrategyCreate(StrategyBase):
    pass

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class StrategyInDB(StrategyBase):
    id: int
    status: str
    is_active: bool

    class Config:
        orm_mode = True