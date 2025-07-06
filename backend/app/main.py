# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

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

# 设置CORS跨域资源共享
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许你的Vue前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def create_initial_data():
    db: Session = SessionLocal()
    strategies = crud.get_strategies(db)
    if not strategies:
        sma_strategy_code = """
# 双均线策略示例
from tqsdk import TqApi, TqAuth

api = TqApi(auth=TqAuth("信易账户", "账户", "密码"))
klines = api.get_kline_serial("SHFE.rb2410", 60)
position = api.get_position("SHFE.rb2410")

# 等待K线数据就绪
api.wait_update()

while True:
    api.wait_update()
    if api.is_changing(klines.iloc[-1], "datetime"):
        ma5 = sum(klines.close.iloc[-5:]) / 5
        ma20 = sum(klines.close.iloc[-20:]) / 20
        
        if ma5 > ma20 and position.pos_long == 0:
            print("金叉，买开")
            api.insert_order(symbol="SHFE.rb2410", direction="BUY", offset="OPEN", volume=1, limit_price=klines.close.iloc[-1])
        elif ma5 < ma20 and position.pos_long > 0:
            print("死叉，卖平")
            api.insert_order(symbol="SHFE.rb2410", direction="SELL", offset="CLOSE", volume=1, limit_price=klines.close.iloc[-1])
"""
        
        rsi_strategy_code = """
# RSI 策略示例
import talib
from tqsdk import TqApi, TqAuth

api = TqApi(auth=TqAuth("信易账户", "账户", "密码"))
klines = api.get_kline_serial("SHFE.rb2410", 3600)
position = api.get_position("SHFE.rb2410")

# 等待K线数据就绪
api.wait_update()

while True:
    api.wait_update()
    if api.is_changing(klines.iloc[-1], "datetime"):
        rsi = talib.RSI(klines.close, timeperiod=14)
        
        if rsi.iloc[-1] > 70 and position.pos_short == 0:
            print("RSI > 70, 卖开")
            api.insert_order(symbol="SHFE.rb2410", direction="SELL", offset="OPEN", volume=1, limit_price=klines.close.iloc[-1])
        elif rsi.iloc[-1] < 30 and position.pos_short > 0:
            print("RSI < 30, 买平")
            api.insert_order(symbol="SHFE.rb2410", direction="BUY", offset="CLOSE", volume=1, limit_price=klines.close.iloc[-1])
"""
        
        crud.create_strategy(db, StrategyCreate(name="双均线策略", description="经典的趋势跟踪策略", script_content=sma_strategy_code))
        crud.create_strategy(db, StrategyCreate(name="RSI震荡策略", description="利用RSI指标进行高抛低吸", script_content=rsi_strategy_code))
    db.close()


# 包含v1版本的API路由
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Quant Trading System API"}
