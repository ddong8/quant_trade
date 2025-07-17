# backend/app/schemas/strategy.py
from pydantic import BaseModel
from typing import Optional, List
from .backtest import BacktestResultInfo

# --- 修改: 将脚本内容和参数分开 ---
class StrategyScript(BaseModel):
    content: str

class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    content: Optional[str] = None # 用户可以直接提供内容
    template_name: Optional[str] = None # 或者选择一个模板

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
    owner: str
    backtest_results: List[BacktestResultInfo] = []

    class Config:
        from_attributes = True

# Schema for API responses
class Strategy(StrategyInDB):
    pass