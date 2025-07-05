from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    script_path = Column(String) # 假设策略代码在文件中
    status = Column(String, default="stopped") # "running", "stopped", "error"
    is_active = Column(Boolean(), default=True)