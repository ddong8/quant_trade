from pydantic import BaseModel, Field
from datetime import date

class BacktestRequest(BaseModel):
    symbol: str = Field(..., description="TqSdk合约代码, 例如 'SHFE.rb2501'")
    start_dt: date
    end_dt: date
