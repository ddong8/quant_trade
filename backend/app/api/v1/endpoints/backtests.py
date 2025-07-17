# backend/app/api/v1/endpoints/backtests.py
import uuid
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
    OptimizationParameter,
    OptimizationRequest,
    BacktestRunResponse,
    BacktestResultInfo,
)
from app.tasks import run_backtest_task, run_optimization_task

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
    """
    strategy = crud_strategy.get_strategy(db, strategy_id=strategy_id)
    if not strategy or strategy.owner != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not enough permissions for this strategy")

    backtest_create = BacktestResultCreate(
        strategy_id=strategy_id,
        symbol=backtest_in.symbol,
        duration=backtest_in.duration,
        start_dt=backtest_in.start_dt,
        end_dt=backtest_in.end_dt,
        commission_rate=backtest_in.commission_rate,
        slippage=backtest_in.slippage,
        status="PENDING"
    )
    db_backtest = crud_backtest.create_backtest_result(db, obj_in=backtest_create)

    # 【修正】: 只传递 backtest_id，让任务自己从数据库加载详情
    task = run_backtest_task.delay(db_backtest.id)

    crud_backtest.update_backtest_result(db, db_obj=db_backtest, obj_in={"task_id": task.id})

    return {
        "task_id": task.id,
        "backtest_id": db_backtest.id,
        "status": "PENDING"
    }

@router.post("/optimize/{strategy_id}", response_model=dict)
def run_optimization(
    strategy_id: int,
    optim_request: OptimizationRequest,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Run a new parameter optimization for a given strategy.
    """
    strategy = crud_strategy.get_strategy(db, strategy_id=strategy_id)
    if not strategy or strategy.owner != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not enough permissions for this strategy")

    optimization_id = str(uuid.uuid4())

    # 【修正】: 将 datetime 对象转换为 ISO 格式的字符串，确保可序列化
    serializable_backtest_params = {
        "symbol": optim_request.symbol,
        "duration": optim_request.duration.value, # 传递枚举的值
        "start_dt_iso": optim_request.start_dt.isoformat(),
        "end_dt_iso": optim_request.end_dt.isoformat(),
        "commission_rate": optim_request.commission_rate,
        "slippage": optim_request.slippage,
    }

    run_optimization_task.delay(
        strategy_id=strategy_id,
        backtest_params=serializable_backtest_params,
        optimization_params=[p.model_dump() for p in optim_request.optim_params],
        optimization_id=optimization_id
    )

    return {"message": "Optimization task has been dispatched.", "optimization_id": optimization_id}


@router.get("/history/{strategy_id}", response_model=List[BacktestResultInfo])
def get_backtest_history_for_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
):
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

    db_strategy = crud_strategy.get_strategy(db, strategy_id=db_result.strategy_id)
    if not db_strategy or db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return db_result

@router.get("/optimization/{optimization_id}", response_model=List[BacktestResultInDB])
def get_optimization_results(
    optimization_id: str,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Get all backtest results for a given optimization run.
    """
    results = crud_backtest.get_backtest_results_by_optimization_id(db, optimization_id=optimization_id)
    if not results:
        raise HTTPException(status_code=404, detail="Optimization results not found")

    # Check ownership of the first result's strategy
    strategy_id = results[0].strategy_id
    strategy = crud_strategy.get_strategy(db, strategy_id=strategy_id)
    if not strategy or strategy.owner != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return results