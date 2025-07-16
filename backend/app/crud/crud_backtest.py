# backend/app/crud/crud_backtest.py
from sqlalchemy.orm import Session
from app.models.backtest import BacktestResult
from app.schemas.backtest import BacktestResultCreate, BacktestResultUpdate
from typing import Any, Dict, Union

def create_backtest_result(db: Session, *, obj_in: BacktestResultCreate) -> BacktestResult:
    db_obj = BacktestResult(
        strategy_id=obj_in.strategy_id,
        symbol=obj_in.symbol,
        duration=obj_in.duration,
        start_dt=obj_in.start_dt,
        end_dt=obj_in.end_dt,
        status=obj_in.status,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_backtest_result(db: Session, *, db_obj: BacktestResult, obj_in: Union[BacktestResultUpdate, Dict[str, Any]]) -> BacktestResult:
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_obj, field, value)
        
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_backtest_result(db: Session, backtest_id: int):
    return db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()

def get_backtest_results_by_strategy(db: Session, strategy_id: int, skip: int = 0, limit: int = 100):
    results = db.query(BacktestResult).filter(BacktestResult.strategy_id == strategy_id).order_by(BacktestResult.created_at.desc()).offset(skip).limit(limit).all()
    
    response_data = []
    for result in results:
        summary = result.summary or {}
        response_data.append({
            "id": result.id,
            "created_at": result.created_at,
            "status": result.status,
            "summary": summary, # 返回完整的summary
            "sharpe_ratio": summary.get("sharpe_ratio"),
            "max_drawdown": summary.get("max_drawdown"),
        })
    return response_data