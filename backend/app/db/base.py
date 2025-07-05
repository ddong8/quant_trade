from sqlalchemy.ext.declarative import declarative_base
from .session import engine

Base = declarative_base()

def init_db():
    # 在这里导入所有定义了模型的模块，以便它们在元数据中注册
    from app.models.strategy import Strategy
    Base.metadata.create_all(bind=engine)