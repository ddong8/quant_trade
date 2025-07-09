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

# 包含v1版本的API路由
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Quant Trading System API"}
