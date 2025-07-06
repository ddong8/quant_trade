# backend/app/api/v1/endpoints/strategies.py
import sys
import asyncio
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
import app.crud.crud_strategy as crud
from app.schemas.strategy import Strategy, StrategyCreate, StrategyUpdate, StrategyInDB
from app.services.websocket_manager import manager

router = APIRouter()

# A dictionary to keep track of running strategy processes
# { strategy_id: asyncio.subprocess.Process }
running_strategies: Dict[int, asyncio.subprocess.Process] = {}

async def stream_logs(stream: asyncio.StreamReader, strategy_id: int, log_type: str):
    """Asynchronously read a stream and broadcast logs."""
    while not stream.at_eof():
        line = await stream.readline()
        if line:
            message = {
                "type": "log",
                "data": {
                    "strategy_id": strategy_id,
                    "log_type": log_type,
                    "message": line.decode().strip()
                }
            }
            await manager.broadcast(message)

@router.post("/", response_model=StrategyInDB)
def create_strategy(
    *,
    db: Session = Depends(deps.get_db),
    strategy_in: StrategyCreate,
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Create new strategy. (This remains synchronous)
    """
    strategy = crud.create_strategy(db=db, strategy=strategy_in)
    return strategy

@router.get("/", response_model=List[StrategyInDB])
def read_strategies(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Retrieve strategies. (This remains synchronous)
    """
    strategies = crud.get_strategies(db, skip=skip, limit=limit)
    return strategies

@router.put("/{strategy_id}", response_model=Strategy)
def update_strategy(
    *,
    db: Session = Depends(deps.get_db),
    strategy_id: int,
    strategy_in: StrategyUpdate,
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Update a strategy. (This remains synchronous)
    """
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy_id in running_strategies and running_strategies[strategy_id].returncode is None:
        raise HTTPException(status_code=400, detail="Cannot edit a running strategy. Please stop it first.")

    updated_strategy = crud.update_strategy(db=db, strategy_id=strategy_id, strategy_in=strategy_in)
    return updated_strategy

@router.get("/{strategy_id}/script", response_model=dict)
def get_strategy_script(
    *,
    db: Session = Depends(deps.get_db),
    strategy_id: int,
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Get the script content of a strategy. (This remains synchronous)
    """
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    try:
        with open(db_strategy.script_path, "r") as f:
            content = f.read()
        return {"script_content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Script file not found")

@router.post("/{strategy_id}/start", response_model=Strategy)
async def start_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """Start a strategy and background tasks to stream its logs."""
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy_id in running_strategies and running_strategies[strategy_id].returncode is None:
        raise HTTPException(status_code=400, detail="Strategy is already running")

    script_path = db_strategy.script_path
    
    process = await asyncio.create_subprocess_exec(
        sys.executable, script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    running_strategies[strategy_id] = process

    # Start background tasks to stream logs
    asyncio.create_task(stream_logs(process.stdout, strategy_id, "stdout"))
    asyncio.create_task(stream_logs(process.stderr, strategy_id, "stderr"))
    
    # This part needs to run in a threadpool as it's synchronous DB access
    updated_strategy = await asyncio.to_thread(crud.update_strategy_status, db, strategy_id=strategy_id, status="running")
    return updated_strategy

@router.post("/{strategy_id}/stop", response_model=Strategy)
async def stop_strategy(
    strategy_id: int,
    db: Session = Depends(deps.get_db),
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Stops a strategy if it's running, and cleans up its state regardless.
    This endpoint is idempotent and safe to call even if the strategy has already stopped.
    """
    process = running_strategies.get(strategy_id)

    if process and process.returncode is None:
        # Process is running, terminate it gracefully
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill() # Force kill if it doesn't terminate
            await process.wait()

    # Clean up the entry from the dictionary if it exists
    if strategy_id in running_strategies:
        del running_strategies[strategy_id]

    # Always update the database to 'stopped' to ensure consistency
    updated_strategy = await asyncio.to_thread(
        crud.update_strategy_status, db, strategy_id=strategy_id, status="stopped"
    )
    
    if not updated_strategy:
        # This case might happen if the strategy_id is invalid to begin with
        raise HTTPException(status_code=404, detail="Strategy not found in database")

    return updated_strategy

@router.delete("/{strategy_id}", response_model=Strategy)
def delete_strategy(
    *,
    db: Session = Depends(deps.get_db),
    strategy_id: int,
    current_user: dict = Depends(deps.get_current_user),
):
    """
    Delete a strategy. (This remains synchronous)
    """
    db_strategy = crud.get_strategy(db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy_id in running_strategies and running_strategies[strategy_id].returncode is None:
        raise HTTPException(status_code=400, detail="Cannot delete a running strategy. Please stop it first.")

    deleted_strategy = crud.delete_strategy(db=db, strategy_id=strategy_id)
    return deleted_strategy