from sqlalchemy.orm import Session
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate

def get_strategy(db: Session, strategy_id: int):
    return db.query(Strategy).filter(Strategy.id == strategy_id).first()

def get_strategies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Strategy).offset(skip).limit(limit).all()

def create_strategy(db: Session, strategy: StrategyCreate):
    db_strategy = Strategy(**strategy.dict())
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

def update_strategy_status(db: Session, strategy_id: int, status: str):
    db_strategy = get_strategy(db, strategy_id)
    if db_strategy:
        db_strategy.status = status
        db.commit()
        db.refresh(db_strategy)
    return db_strategy