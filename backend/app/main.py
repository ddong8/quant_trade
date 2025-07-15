# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path

from app.api.v1.api import api_router
from app.core.config import SECRET_KEY
from app.db.base import init_db
from app.db.session import SessionLocal
import app.crud.crud_strategy as crud
from app.schemas.strategy import StrategyCreate

# 在应用启动时创建数据库表
init_db()

app = FastAPI(
    title="Quant Trading System API",
    openapi_url="/api/v1/openapi.json"
)

@app.on_event("startup")
def startup_event():
    """
    On startup, check for demo strategies and ensure their script files exist.
    """
    db: Session = SessionLocal()
    
    print("--- Running startup script: Verifying strategy files ---")

    # 1. Define the demo strategy details
    demo_strategy_name = "MA Crossover Strategy"
    demo_strategy_description = "A simple moving average crossover strategy compatible with the backtester."
    demo_strategy_script = """
import pandas as pd

def run_strategy(data: pd.DataFrame):
    '''
    A simple moving average crossover strategy.

    Args:
        data: A pandas DataFrame with columns ['date', 'open', 'high', 'low', 'close', 'volume'].

    Returns:
        A list of dictionaries, where each dictionary represents a signal.
        e.g., [{'date': '2023-01-10', 'signal': 'buy'}, {'date': '2023-02-20', 'signal': 'sell'}]
    '''
    # --- Strategy Parameters ---
    short_window = 20
    long_window = 50

    # --- Signal Generation ---
    signals = []
    
    # Calculate moving averages
    data['short_mavg'] = data['close'].rolling(window=short_window, min_periods=1, center=False).mean()
    data['long_mavg'] = data['close'].rolling(window=long_window, min_periods=1, center=False).mean()

    # Create signals
    data['signal'] = 0.0
    # Generate signal when short MA crosses above long MA
    data['signal'][short_window:] = (data['short_mavg'][short_window:] > data['long_mavg'][short_window:]).astype(float)

    # Generate trading orders
    data['positions'] = data['signal'].diff()

    for i in range(len(data)):
        if data['positions'][i] == 1.0:
            signals.append({'date': data['trade_date'][i], 'signal': 'buy'})
        elif data['positions'][i] == -1.0:
            signals.append({'date': data['trade_date'][i], 'signal': 'sell'})
            
    return signals
"""

    # 2. Check if the demo strategy exists in the DB
    db_strategy = crud.get_strategy_by_name(db, name=demo_strategy_name)
    
    if not db_strategy:
        # If not, create it in the DB. The CRUD function will also create the file.
        print(f"Demo strategy '{demo_strategy_name}' not found in DB. Creating it...")
        strategy_to_create = StrategyCreate(
            name=demo_strategy_name,
            description=demo_strategy_description,
            script_content=demo_strategy_script
        )
        crud.create_strategy(db=db, strategy=strategy_to_create, owner="admin")
        print("Demo strategy created.")
    else:
        # If it exists in the DB, ensure its corresponding file also exists.
        print(f"Demo strategy '{demo_strategy_name}' found in DB. Verifying file...")
        if db_strategy.script_path:
            p = Path(db_strategy.script_path)
            if not p.exists():
                print(f"File not found at {p}. Re-creating it...")
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(demo_strategy_script)
                    print("File re-created successfully.")
                except Exception as e:
                    print(f"Error re-creating file: {e}")
            else:
                print("File already exists. No action needed.")
        else:
            print("Strategy exists in DB but has no script path. This is an inconsistent state.")

    db.close()
    print("--- Startup script finished ---")


# 设置CORS跨域资源共享
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许你的Vue前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含v1版本的API路由
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Quant Trading System API"}
