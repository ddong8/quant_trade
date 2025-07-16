# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
from contextlib import asynccontextmanager

from app.api.v1.api import api_router
from app.core.config import SECRET_KEY
from app.db.base import init_db
from app.db.session import SessionLocal
import app.crud.crud_strategy as crud
from app.schemas.strategy import StrategyCreate

# 在应用启动时创建数据库表
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 这是应用启动时执行的逻辑 ---
    print("--- Running startup logic via lifespan manager ---")
    db: Session = SessionLocal()
    
    # 1. 定义演示策略的详细信息
    demo_strategy_name = "MA Crossover Strategy"
    demo_strategy_description = "A simple moving average crossover strategy compatible with the backtester."
    demo_strategy_script = """import pandas as pd
from app.services.strategy_base import BaseStrategy

class Strategy(BaseStrategy):
    def set_parameters(self):
        # 在这里声明所有可优化的参数及其默认值
        self.short_window = 20
        self.long_window = 50

    def initialize(self):
        self.symbol = "SHFE.rb2501"  # 交易的合约

    def handle_data(self, data: pd.DataFrame):
        '''
        Args:
            data: 一个包含最新K线数据的 pandas DataFrame。
                  在我们的回测器中，它包含所有历史数据。
                  在实盘中，它可能只包含最近的N条数据。
        '''
        # --- 信号生成 ---
        signals = []
        
        # 计算移动平均线
        short_mavg = data['close'].rolling(window=self.short_window).mean()
        long_mavg = data['close'].rolling(window=self.long_window).mean()

        # 创建信号：当短期均线上穿长期均线时为1，下穿时为-1
        # .iloc[-1] 获取最新值
        if short_mavg.iloc[-1] > long_mavg.iloc[-1] and short_mavg.iloc[-2] < long_mavg.iloc[-2]:
            return [{'date': data['trade_date'].iloc[-1], 'signal': 'buy'}]
        elif short_mavg.iloc[-1] < long_mavg.iloc[-1] and short_mavg.iloc[-2] > long_mavg.iloc[-2]:
            return [{'date': data['trade_date'].iloc[-1], 'signal': 'sell'}]
        
        return []
"""
    # 2. 检查并创建策略
    db_strategy = crud.get_strategy_by_name(db, name=demo_strategy_name)
    
    if not db_strategy:
        print(f"Demo strategy '{demo_strategy_name}' not found in DB. Creating it...")
        strategy_to_create = StrategyCreate(
            name=demo_strategy_name,
            description=demo_strategy_description,
            content=demo_strategy_script
        )
        crud.create_strategy(db=db, strategy=strategy_to_create, owner="admin")
        print("Demo strategy created.")
    else:
        print(f"Demo strategy '{demo_strategy_name}' found in DB. Verifying file...")
        if db_strategy.script_path:
            p = Path(db_strategy.script_path)
            # 无论文件是否存在，都用最新的代码覆盖它，以确保格式正确
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(demo_strategy_script)
                print("Demo strategy file verified and updated.")
            except Exception as e:
                print(f"Error updating demo strategy file: {e}")
        else:
            print("Strategy exists in DB but has no script path. This is an inconsistent state.")

    db.close()
    print("--- Startup logic finished ---")

    yield

    # --- 这是应用关闭时执行的逻辑 (如果需要的话) ---
    # print("--- Running shutdown logic ---")


# 将 lifespan 管理器注册到 FastAPI 应用
app = FastAPI(
    title="Quant Trading System API",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)


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