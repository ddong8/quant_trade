# backend/app/api/v1/endpoints/strategies.py
import json
import sys
import os
import asyncio
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
import app.crud.crud_strategy as crud
from app.schemas.strategy import Strategy, StrategyCreate, StrategyUpdate, StrategyInDB
from app.schemas.backtest import BacktestRequest
from app.services.websocket_manager import manager

router = APIRouter()

# --- Demo Strategy Code ---
SMA_STRATEGY_CODE = """
import os
import json
from datetime import date
from tqsdk import TqApi, TqAuth, TqBacktest

# 从环境变量读取回测日期
start_dt_str = os.environ.get("TQ_BACKTEST_START_DT")
end_dt_str = os.environ.get("TQ_BACKTEST_END_DT")
is_backtest = start_dt_str and end_dt_str

backtest_options = {}
if is_backtest:
    backtest_options["backtest"] = TqBacktest(
        start_dt=date.fromisoformat(start_dt_str), 
        end_dt=date.fromisoformat(end_dt_str)
    )
    print(f"进入回测模式: {start_dt_str} to {end_dt_str}")

# 在创建TqApi实例时，请传入自己的信易账户, TqAuth("信易账户", "账户", "密码")
api = TqApi(auth=TqAuth("信易账户", "账户", "密码"), **backtest_options)
klines = api.get_kline_serial("SHFE.rb2410", 60)
position = api.get_position("SHFE.rb2410")

try:
    api.wait_update()
    print("策略开始运行")
    while True:
        api.wait_update()
        if api.is_changing(klines.iloc[-1], "datetime"):
            ma5 = sum(klines.close.iloc[-5:]) / 5
            ma20 = sum(klines.close.iloc[-20:]) / 20
            if ma5 > ma20 and position.pos_long == 0:
                print(f"金叉，MA5={ma5:.2f}, MA20={ma20:.2f}，买开")
                api.insert_order(symbol="SHFE.rb2410", direction="BUY", offset="OPEN", volume=1, limit_price=klines.close.iloc[-1])
            elif ma5 < ma20 and position.pos_long > 0:
                print(f"死叉，MA5={ma5:.2f}, MA20={ma20:.2f}，卖平")
                api.insert_order(symbol="SHFE.rb2410", direction="SELL", offset="CLOSE", volume=1, limit_price=klines.close.iloc[-1])
finally:
    if is_backtest:
        summary = api.get_backtest_summary(as_json=True)
        print(f"BACKTEST_SUMMARY:{json.dumps(summary)}")
    api.close()
"""

RSI_STRATEGY_CODE = """
# -- 策略参数 --
# !!! 重要: 请在此处替换为您自己的信易账户信息 !!!
TQ_ACCOUNT = "信易账户"
TQ_USER_NAME = "账户"
TQ_PASSWORD = "密码"
# !!! 重要: 请根据需要修改合约代码 !!!
SYMBOL = "SHFE.rb2410"

# -- 策略逻辑 --
import os
import json
import talib
from datetime import date
from tqsdk import TqApi, TqAuth, TqBacktest

start_dt_str = os.environ.get("TQ_BACKTEST_START_DT")
end_dt_str = os.environ.get("TQ_BACKTEST_END_DT")
is_backtest = start_dt_str and end_dt_str

backtest_options = {}
if is_backtest:
    backtest_options["backtest"] = TqBacktest(
        start_dt=date.fromisoformat(start_dt_str), 
        end_dt=date.fromisoformat(end_dt_str)
    )
    print(f"进入回测模式: {start_dt_str} to {end_dt_str}")

api = TqApi(auth=TqAuth(TQ_ACCOUNT, TQ_USER_NAME, TQ_PASSWORD), **backtest_options)
klines = api.get_kline_serial(SYMBOL, 3600)
position = api.get_position(SYMBOL)

try:
    api.wait_update()
    print("策略开始运行")
    while True:
        api.wait_update()
        if api.is_changing(klines.iloc[-1], "datetime"):
            rsi = talib.RSI(klines.close, timeperiod=14)
            if rsi.iloc[-1] > 70 and position.pos_short == 0:
                print(f"RSI > 70 ({rsi.iloc[-1]:.2f}), 卖开")
                api.insert_order(symbol=SYMBOL, direction="SELL", offset="OPEN", volume=1, limit_price=klines.close.iloc[-1])
            elif rsi.iloc[-1] < 30 and position.pos_short > 0:
                print(f"RSI < 30 ({rsi.iloc[-1]:.2f}), 买平")
                api.insert_order(symbol=SYMBOL, direction="BUY", offset="CLOSE", volume=1, limit_price=klines.close.iloc[-1])
finally:
    if is_backtest:
        summary = api.get_backtest_summary(as_json=True)
        print(f"BACKTEST_SUMMARY:{json.dumps(summary)}")
    api.close()
"""

running_strategies: Dict[int, asyncio.subprocess.Process] = {}

async def stream_logs(stream: asyncio.StreamReader, strategy_id: int, log_type: str):
    """Asynchronously read a stream and broadcast logs, checking for backtest summary."""
    while not stream.at_eof():
        line_bytes = await stream.readline()
        if line_bytes:
            line = line_bytes.decode().strip()
            if line.startswith("BACKTEST_SUMMARY:"):
                try:
                    # Extract and parse the JSON part
                    summary_json = line.split(":", 1)[1]
                    summary_data = json.loads(summary_json)
                    message = {"type": "backtest_result", "data": {"strategy_id": strategy_id, "summary": summary_data}}
                except (IndexError, json.JSONDecodeError) as e:
                    # If parsing fails, send as a normal log
                    message = {"type": "log", "data": {"strategy_id": strategy_id, "log_type": "error", "message": f"Failed to parse backtest summary: {line}"}}
            else:
                # Regular log message
                message = {"type": "log", "data": {"strategy_id": strategy_id, "log_type": log_type, "message": line}}
            
            await manager.broadcast(message)

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
        crud.create_strategy(db, StrategyCreate(name="RSI震荡策略 (Demo)", description="利用RSI指标进行高抛低吸", script_content=RSI_STRATEGY_CODE), owner=owner)
        strategies = crud.get_strategies(db, owner=owner, skip=skip, limit=limit)
    return strategies

# ... (rest of the endpoints remain the same) ...
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
    if strategy_id in running_strategies and running_strategies[strategy_id].returncode is None:
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
        with open(db_strategy.script_path, "r") as f:
            content = f.read()
        return {"script_content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script file not found")

@router.post("/{strategy_id}/start", response_model=Strategy)
async def start_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    db_strategy = await asyncio.to_thread(crud.get_strategy, db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if strategy_id in running_strategies and running_strategies[strategy_id].returncode is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Strategy is already running")

    process = await asyncio.create_subprocess_exec(
        sys.executable, db_strategy.script_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    running_strategies[strategy_id] = process
    asyncio.create_task(stream_logs(process.stdout, strategy_id, "stdout"))
    asyncio.create_task(stream_logs(process.stderr, strategy_id, "stderr"))
    
    updated_strategy = await asyncio.to_thread(crud.update_strategy_status, db, strategy_id=strategy_id, status="running")
    return updated_strategy

@router.post("/{strategy_id}/stop", response_model=Strategy)
async def stop_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    db_strategy = await asyncio.to_thread(crud.get_strategy, db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    process = running_strategies.get(strategy_id)
    if process and process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
    if strategy_id in running_strategies:
        del running_strategies[strategy_id]

    updated_strategy = await asyncio.to_thread(crud.update_strategy_status, db, strategy_id=strategy_id, status="stopped")
    return updated_strategy

@router.post("/{strategy_id}/backtest", response_model=Strategy)
async def backtest_strategy(
    strategy_id: int,
    backtest_in: BacktestRequest,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """Run a strategy in backtest mode."""
    db_strategy = await asyncio.to_thread(crud.get_strategy, db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if db_strategy.owner != current_user["username"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if strategy_id in running_strategies and running_strategies[strategy_id].returncode is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Strategy is already running")

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["TQ_BACKTEST_START_DT"] = backtest_in.start_dt.isoformat()
    env["TQ_BACKTEST_END_DT"] = backtest_in.end_dt.isoformat()

    process = await asyncio.create_subprocess_exec(
        sys.executable, db_strategy.script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    
    running_strategies[strategy_id] = process
    asyncio.create_task(stream_logs(process.stdout, strategy_id, "stdout"))
    asyncio.create_task(stream_logs(process.stderr, strategy_id, "stderr"))
    
    # We don't change the status in DB for backtests, or we could add a 'backtesting' status
    return db_strategy

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
    if strategy_id in running_strategies and running_strategies[strategy_id].returncode is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a running strategy")

    deleted_strategy = crud.delete_strategy(db=db, strategy_id=strategy_id)
    return deleted_strategy