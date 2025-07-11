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
    summary: Dict[str, Any]
    daily_pnl: List[Dict[str, Any]]

# Properties to return to client
class BacktestResultInDB(BacktestResultCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_encoder
        }

class BacktestResultInfo(BaseModel):
    id: int
    created_at: datetime
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: datetime_encoder
        }
