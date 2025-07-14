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
    demo_strategy_name = "Simple MA Cross"
    demo_strategy_description = "A simple moving average cross strategy."
    demo_strategy_script = """# 这是一个简单的双均线策略示例
# 当短期均线（如5日线）上穿长期均线（如20日线）时，做多
# 当短期均线下穿长期均线时，平仓

def initialize(context):
    # 设置策略参数
    context.short_ma = 5
    context.long_ma = 20
    context.symbol = 'SHFE.rb2501' # 订阅的合约
    context.amount = 1 # 每次下单手数

    # 订阅行情
    context.subscribe(context.symbol)

def handle_data(context, data):
    # 获取历史数据
    hist = context.history(context.symbol, 'close', context.long_ma + 1, '1d')
    if hist is None or len(hist) < context.long_ma:
        return

    # 计算均线
    short_ma = hist[-context.short_ma:].mean()
    long_ma = hist[-context.long_ma:].mean()

    # 获取当前持仓
    position = context.get_position(context.symbol)

    # 金叉：短期均线上穿长期均线
    if short_ma > long_ma and position is None:
        print(f"金叉形成，在价格 {data.close} 买入")
        context.buy(context.symbol, context.amount)

    # 死叉：短期均线下穿长期均线
    elif short_ma < long_ma and position is not None:
        print(f"死叉形成，在价格 {data.close} 平仓")
        context.sell(context.symbol, position.volume)
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
