from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    script_path = Column(String)
    status = Column(String, default="stopped")
    is_active = Column(Boolean(), default=True)
    owner = Column(String, index=True)

    backtest_results = relationship("BacktestResult", back_populates="strategy", cascade="all, delete-orphan")
