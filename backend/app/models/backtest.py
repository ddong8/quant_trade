from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base

class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Store performance summary and daily PNL data
    summary = Column(JSON)
    daily_pnl = Column(JSON)

    strategy = relationship("Strategy", back_populates="backtest_results")
