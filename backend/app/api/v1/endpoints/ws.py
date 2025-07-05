# backend/app/api/v1/endpoints/ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager

router = APIRouter()

@router.websocket("/data")
async def websocket_endpoint(websocket: WebSocket):
    """处理WebSocket连接，用于推送实时数据"""
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接，等待后端从其他地方推送消息
            # 客户端发来的消息可以被忽略或处理
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)