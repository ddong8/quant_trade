from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.schemas.backtest import KlineDuration # Import Enum for use in model

class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    optimization_id = Column(String, index=True, nullable=True) # Link to an optimization run
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Celery task ID
    task_id = Column(String, index=True, nullable=True)

    # Backtest parameters
    symbol = Column(String, nullable=False)
    duration = Column(Enum(KlineDuration), nullable=False)
    start_dt = Column(DateTime, nullable=False)
    end_dt = Column(DateTime, nullable=False)
    commission_rate = Column(Float, nullable=False, default=0.0003)
    slippage = Column(Float, nullable=False, default=0.0)

    # Status of the backtest run
    status = Column(String, nullable=False, default='PENDING')
    
    # Store performance summary and daily PNL data
    summary = Column(JSON, nullable=True)
    daily_pnl = Column(JSON, nullable=True)

    strategy = relationship("Strategy", back_populates="backtest_results")
