# backend/app/schemas/backtest.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import pytz

def datetime_encoder(dt: datetime) -> str:
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        utc_dt = pytz.utc.localize(dt)
    else:
        utc_dt = dt.astimezone(pytz.utc)
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    return utc_dt.astimezone(shanghai_tz).isoformat()

class KlineDuration(str, Enum):
    one_minute = "1m"
    five_minutes = "5m"
    fifteen_minutes = "15m"
    one_hour = "1h"
    one_day = "1d"

# --- 新增: 参数优化请求 ---
class OptimizationParameter(BaseModel):
    name: str # 参数名, e.g., "short_window"
    start: float
    end: float
    step: float

class BacktestRequest(BaseModel):
    symbol: str
    duration: KlineDuration
    start_dt: datetime
    end_dt: datetime

# Shared properties
class BacktestResultBase(BaseModel):
    strategy_id: int

# Properties to receive on creation
class BacktestResultCreate(BacktestResultBase):
    symbol: str
    duration: KlineDuration
    start_dt: datetime
    end_dt: datetime
    status: str = "PENDING"

# Properties to receive on update
class BacktestResultUpdate(BaseModel):
    task_id: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    daily_pnl: Optional[Dict[str, Any]] = None

# Properties to return to client
class BacktestResultInDB(BacktestResultCreate):
    id: int
    created_at: datetime
    summary: Optional[Dict[str, Any]] = None
    daily_pnl: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_encoder
        }

class BacktestResultInfo(BaseModel):
    id: int
    created_at: datetime
    status: str
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_encoder
        }


class BacktestRunResponse(BaseModel):
    task_id: Optional[str] = None
    backtest_id: int