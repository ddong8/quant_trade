# backend/app/api/v1/endpoints/backtests.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
import app.crud.crud_strategy as crud_strategy
import app.crud.crud_backtest as crud_backtest
from app.schemas.backtest import BacktestResultInDB

router = APIRouter()

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
