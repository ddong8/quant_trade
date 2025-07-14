from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, List
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
    task_id: str | None = None
    status: str | None = None
    summary: Dict[str, Any] | None = None
    daily_pnl: List[Dict[str, Any]] | None = None

# Properties to return to client
class BacktestResultInDB(BacktestResultCreate):
    id: int
    created_at: datetime
    summary: Dict[str, Any] | None = None
    daily_pnl: List[Dict[str, Any]] | None = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_encoder
        }

class BacktestResultInfo(BaseModel):
    id: int
    created_at: datetime
    status: str
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_encoder
        }


class BacktestRunResponse(BaseModel):
    task_id: str | None = None
    backtest_id: int
