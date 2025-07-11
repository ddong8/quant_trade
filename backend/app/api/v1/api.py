# backend/app/api/v1/api.py

from fastapi import APIRouter

from app.api.v1.endpoints import login, strategies, ws, backtests

api_router = APIRouter()

# 包含各个模块的路由
api_router.include_router(login.router, tags=["login"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(ws.router, prefix="/ws", tags=["websockets"])
api_router.include_router(backtests.router, prefix="/backtests", tags=["backtests"])