from sqlalchemy.orm import Session
from app.models.backtest import BacktestResult
from app.schemas.backtest import BacktestResultCreate

def create_backtest_result(db: Session, *, obj_in: BacktestResultCreate) -> BacktestResult:
    db_obj = BacktestResult(
        strategy_id=obj_in.strategy_id,
        summary=obj_in.summary,
        daily_pnl=obj_in.daily_pnl
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_backtest_result(db: Session, backtest_id: int):
    return db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()

def get_backtest_results_by_strategy(db: Session, strategy_id: int, skip: int = 0, limit: int = 100):
    results = db.query(BacktestResult).filter(BacktestResult.strategy_id == strategy_id).offset(skip).limit(limit).all()
    # Pydantic v2's from_attributes doesn't automatically handle nested JSON fields well.
    # We can manually construct the data for the schema.
    response_data = []
    for result in results:
        summary = result.summary or {}
        response_data.append({
            "id": result.id,
            "created_at": result.created_at,
            "sharpe_ratio": summary.get("sharpe_ratio"),
            "max_drawdown": summary.get("max_drawdown"),
        })
    return response_data
