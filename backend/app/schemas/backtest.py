from pydantic import BaseModel
from datetime import date

class BacktestRequest(BaseModel):
    start_dt: date
    end_dt: date
