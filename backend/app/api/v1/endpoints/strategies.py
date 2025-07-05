# backend/app/api/v1/endpoints/strategies.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
import app.crud.crud_strategy as crud
from app.schemas.strategy import StrategyCreate, StrategyInDB
from app.services.mock_tq_runner import start_strategy_runner, stop_strategy_runner

router = APIRouter()

@router.get("/", response_model=List[StrategyInDB])
def read_strategies(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(deps.get_current_user),
):
    """
    获取策略列表。
    首次运行时会创建一些示例数据。
    """
    strategies = crud.get_strategies(db, skip=skip, limit=limit)
    if not strategies:
        crud.create_strategy(db, StrategyCreate(name="双均线策略", description="经典的趋势跟踪策略", script_path="sma_cross.py"))
        crud.create_strategy(db, StrategyCreate(name="RSI震荡策略", description="利用RSI指标进行高抛低吸", script_path="rsi_oscillator.py"))
        strategies = crud.get_strategies(db)
    return strategies


@router.post("/{strategy_id}/start", response_model=StrategyInDB)
def start_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """启动一个策略"""
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    start_strategy_runner(strategy_id)
    updated_strategy = crud.update_strategy_status(db, strategy_id=strategy_id, status="running")
    return updated_strategy


@router.post("/{strategy_id}/stop", response_model=StrategyInDB)
def stop_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """停止一个策略"""
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    stop_strategy_runner(strategy_id)
    updated_strategy = crud.update_strategy_status(db, strategy_id=strategy_id, status="stopped")
    return updated_strategy