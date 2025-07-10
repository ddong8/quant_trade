# backend/app/api/v1/endpoints/strategies.py
import json
import sys
import os
import asyncio
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.api import deps
import app.crud.crud_strategy as crud
from app.schemas.strategy import Strategy, StrategyCreate, StrategyUpdate, StrategyInDB
from app.schemas.backtest import BacktestRequest
from app.services.websocket_manager import manager
# --- 新增导入 ---
from app.services.backtester import run_backtest_for_strategy
from app.services.mock_tq_runner import start_strategy_runner, stop_strategy_runner

router = APIRouter()

# --- Demo Strategy Code (可以保留作为新用户的示例代码) ---
SMA_STRATEGY_CODE = """
# 这是一个简单的双均线策略示例
# 平台会自动注入 `data` (一个包含OHLCV的DataFrame)
# 您需要实现一个 `run_strategy` 函数

import pandas as pd

def run_strategy(data: pd.DataFrame):
    # 计算5日和10日移动平均线
    data['ma5'] = data['close'].rolling(window=5).mean()
    data['ma10'] = data['close'].rolling(window=10).mean()
    
    signals = []
    for i in range(1, len(data)):
        # 金叉买入信号
        if data.loc[i-1, 'ma5'] < data.loc[i-1, 'ma10'] and data.loc[i, 'ma5'] > data.loc[i, 'ma10']:
            signals.append({'date': data.loc[i, 'trade_date'], 'signal': 'buy'})
        # 死叉卖出信号
        elif data.loc[i-1, 'ma5'] > data.loc[i-1, 'ma10'] and data.loc[i, 'ma5'] < data.loc[i, 'ma10']:
            signals.append({'date': data.loc[i, 'trade_date'], 'signal': 'sell'})
            
    return signals
"""

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
    if not strategies:
        owner = current_user["username"]
        crud.create_strategy(db, StrategyCreate(name="双均线策略 (Demo)", description="经典的趋势跟踪策略", script_content=SMA_STRATEGY_CODE), owner=owner)
        strategies = crud.get_strategies(db, owner=owner, skip=skip, limit=limit)
    
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
    
    return {"script_content": db_strategy.script_content}

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

# --- 新的回测实现 ---
async def run_backtest_and_notify(db: Session, strategy_id: int, symbol: str, start_dt: str, end_dt: str):
    """
    执行回测并通过WebSocket发送结果的后台任务
    """
    print(f"Starting backtest for strategy {strategy_id} on {symbol} from {start_dt} to {end_dt}")
    try:
        # 从数据库获取策略实体
        db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
        if not db_strategy:
            raise FileNotFoundError("Strategy not found in database.")
        
        # 读取策略代码文件内容
        with open(db_strategy.script_path, "r") as f:
            strategy_code = f.read()

        # 运行回测
        result = await asyncio.to_thread(
            run_backtest_for_strategy, 
            strategy_id, 
            strategy_code,
            symbol,
            start_dt, 
            end_dt
        )
        message = {"type": "backtest_result", "data": result}
        await manager.broadcast(message)
        print(f"Backtest for strategy {strategy_id} completed and results sent.")
    except Exception as e:
        print(f"An error occurred during backtest for strategy {strategy_id}: {e}")
        error_message = {"type": "backtest_result", "data": {"strategy_id": strategy_id, "summary": {"error": str(e)}}}
        await manager.broadcast(error_message)

@router.post("/{strategy_id}/backtest")
async def backtest_strategy(
    strategy_id: int,
    backtest_in: BacktestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """使用新的回测服务运行策略回测"""
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if running_strategies.get(strategy_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot backtest a running strategy")

    # 将耗时的回测任务添加到后台
    background_tasks.add_task(
        run_backtest_and_notify,
        db,
        strategy_id,
        backtest_in.symbol,
        backtest_in.start_dt.isoformat(),
        backtest_in.end_dt.isoformat()
    )
    
    # 立即返回，告知前端任务已启动
    return {"message": "Backtest started in the background. Results will be sent via WebSocket."}

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