# backend/app/api/v1/endpoints/strategies.py
import json
import sys
import os
import asyncio
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pathlib import Path

from app.api import deps
import app.crud.crud_strategy as crud
import app.crud.crud_backtest as crud_backtest
from app.schemas.strategy import Strategy, StrategyCreate, StrategyUpdate, StrategyInDB
from app.schemas.backtest import BacktestRequest, KlineDuration, BacktestResultInDB, BacktestResultInfo, BacktestResultCreate, BacktestRunResponse
from app.services.websocket_manager import manager
from app.tasks import run_backtest_task
from app.services.mock_tq_runner import start_strategy_runner, stop_strategy_runner

router = APIRouter()


# --- 策略运行状态管理 ---
# 注意：这里的 running_strategies 现在只用于管理模拟实时运行的策略
running_strategies: Dict[int, bool] = {}

# --- CRUD 和其他端点 ---
@router.post("/", response_model=StrategyInDB)
def create_strategy(
    *,
    db: Session = Depends(deps.get_db),
    strategy_in: StrategyCreate,
    current_user: dict = Depends(deps.get_current_user),
):
    strategy = crud.create_strategy(db=db, strategy=strategy_in, owner=current_user["username"])
    return strategy

@router.get("/", response_model=List[StrategyInDB])
def read_strategies(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(deps.get_current_user),
):
    strategies = crud.get_strategies(db, owner=current_user["username"], skip=skip, limit=limit)
    
    # 同步运行状态
    for s in strategies:
        s.status = "running" if running_strategies.get(s.id) else "stopped"
    return strategies

@router.put("/{strategy_id}", response_model=Strategy)
def update_strategy(
    *,
    db: Session = Depends(deps.get_db),
    strategy_id: int,
    strategy_in: StrategyUpdate,
    current_user: dict = Depends(deps.get_current_user),
):
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if running_strategies.get(strategy_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a running strategy")
    
    updated_strategy = crud.update_strategy(db=db, strategy_id=strategy_id, strategy_in=strategy_in)
    return updated_strategy

@router.get("/{strategy_id}/script", response_model=dict)
def get_strategy_script(
    *,
    db: Session = Depends(deps.get_db),
    strategy_id: int,
    current_user: dict = Depends(deps.get_current_user),
):
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    try:
        with open(db_strategy.script_path, "r", encoding="utf-8") as f:
            script_content = f.read()
    except (FileNotFoundError, TypeError, AttributeError):
        # If the file is not found or the path is invalid, return default code
        script_content = "# Strategy script not found or path is invalid."
    
    return {"script_content": script_content}

@router.post("/{strategy_id}/start", response_model=Strategy)
async def start_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if running_strategies.get(strategy_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Strategy is already running")

    start_strategy_runner(strategy_id)
    running_strategies[strategy_id] = True
    db_strategy.status = "running"
    return db_strategy

@router.post("/{strategy_id}/stop", response_model=Strategy)
async def stop_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    if running_strategies.get(strategy_id):
        stop_strategy_runner(strategy_id)
        del running_strategies[strategy_id]
    
    db_strategy.status = "stopped"
    return db_strategy

@router.post("/{strategy_id}/backtest", response_model=BacktestRunResponse)
def create_backtest_record(
    strategy_id: int,
    backtest_in: BacktestRequest,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Creates a backtest record in the database. The actual backtest is triggered via WebSocket.
    """
    strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not strategy or strategy.owner != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not enough permissions for this strategy")

    backtest_record_in = BacktestResultCreate(
        strategy_id=strategy_id,
        symbol=backtest_in.symbol,
        duration=backtest_in.duration,
        start_dt=backtest_in.start_dt,
        end_dt=backtest_in.end_dt,
        status="PENDING"
    )
    backtest_record = crud_backtest.create_backtest_result(db, obj_in=backtest_record_in)

    # The task is no longer started here. It will be triggered by a WebSocket message.
    # We return the ID so the client knows which WebSocket to connect to.
    return {"task_id": None, "backtest_id": backtest_record.id}


@router.get("/{strategy_id}/backtests", response_model=List[BacktestResultInfo])
def get_strategy_backtest_history(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    results = crud_backtest.get_backtest_results_by_strategy(db, strategy_id=strategy_id)
    return results



@router.delete("/{strategy_id}", response_model=Strategy)
def delete_strategy(
    *,
    db: Session = Depends(deps.get_db),
    strategy_id: int,
    current_user: dict = Depends(deps.get_current_user),
):
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if running_strategies.get(strategy_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a running strategy")

    deleted_strategy = crud.delete_strategy(db=db, strategy_id=strategy_id)
    return deleted_strategy
