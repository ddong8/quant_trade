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
from app.schemas.strategy import StrategyScript
from app.schemas.backtest import BacktestRequest, KlineDuration, BacktestResultInDB, BacktestResultInfo, BacktestResultCreate, BacktestRunResponse
from app.services.websocket_manager import manager
from app.tasks import run_backtest_task
from app.services.live_runner import start_live_runner, stop_live_runner, LIVE_RUNNERS

router = APIRouter()

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
        s.status = "running" if s.id in LIVE_RUNNERS else s.status
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
    if strategy_id in LIVE_RUNNERS:
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
        script_content = "# Strategy script not found or path is invalid."
    
    return {"content": script_content}

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
    if strategy_id in LIVE_RUNNERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Strategy is already running")

    try:
        with open(db_strategy.script_path, "r", encoding="utf-8") as f:
            strategy_code = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Strategy script file not found.")

    main_loop = asyncio.get_running_loop()
    start_live_runner(strategy_id, strategy_code, main_loop)
    
    updated_strategy = crud.update_strategy_status(db=db, strategy_id=strategy_id, status="running")
    return updated_strategy if updated_strategy else db_strategy


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

    stop_live_runner(strategy_id)
    
    updated_strategy = crud.update_strategy_status(db=db, strategy_id=strategy_id, status="stopped")
    return updated_strategy if updated_strategy else db_strategy


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
    if strategy_id in LIVE_RUNNERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a running strategy")

    deleted_strategy = crud.delete_strategy(db=db, strategy_id=strategy_id)
    return deleted_strategy