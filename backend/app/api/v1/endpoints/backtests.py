# backend/app/api/v1/endpoints/backtests.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.api import deps
import app.crud.crud_strategy as crud_strategy
import app.crud.crud_backtest as crud_backtest
from app.schemas.backtest import (
    BacktestRequest,
    BacktestResultInDB,
    BacktestResultCreate,
    BacktestRunResponse,
    BacktestResultInfo,
)
from app.tasks import run_backtest_task

router = APIRouter()

@router.post("/run/{strategy_id}", response_model=BacktestRunResponse)
def run_backtest(
    strategy_id: int,
    backtest_in: BacktestRequest,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Run a new backtest for a given strategy.
    This will create a backtest record and dispatch a Celery task.
    """
    # 1. Verify strategy ownership
    strategy = crud_strategy.get_strategy(db, strategy_id=strategy_id)
    if not strategy or strategy.owner != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not enough permissions for this strategy")

    # 2. Create an initial backtest record in the DB
    backtest_create = BacktestResultCreate(
        strategy_id=strategy_id,
        symbol=backtest_in.symbol,
        duration=backtest_in.duration,
        start_dt=backtest_in.start_dt,
        end_dt=backtest_in.end_dt,
        status="PENDING"
    )
    db_backtest = crud_backtest.create_backtest_result(db, obj_in=backtest_create)

    # 3. Dispatch the Celery task
    task = run_backtest_task.delay(db_backtest.id)

    # 4. Update the record with the task ID
    crud_backtest.update_backtest_result(db, db_obj=db_backtest, obj_in={"task_id": task.id})

    return {
        "task_id": task.id,
        "backtest_id": db_backtest.id,
        "status": "PENDING"
    }


@router.get("/history/{strategy_id}", response_model=List[BacktestResultInfo])
def get_backtest_history_for_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """
    Get the history of backtests for a specific strategy.
    """
    # Verify strategy ownership
    strategy = crud_strategy.get_strategy(db, strategy_id=strategy_id)
    if not strategy or strategy.owner != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not enough permissions for this strategy")

    results = crud_backtest.get_backtest_results_by_strategy(
        db, strategy_id=strategy_id, skip=skip, limit=limit
    )
    return results


@router.get("/{backtest_id}", response_model=BacktestResultInDB)
def get_backtest_report(
    backtest_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    db_result = crud_backtest.get_backtest_result(db, backtest_id=backtest_id)
    if not db_result:
        raise HTTPException(status_code=404, detail="Backtest result not found")

    # Check ownership
    db_strategy = crud_strategy.get_strategy(db, strategy_id=db_result.strategy_id)
    if not db_strategy or db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return db_result
