# backend/app/api/v1/endpoints/ws.py

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager

router = APIRouter()

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接打开，等待后端其他部分通过 manager.broadcast 推送消息
            # 增加一个小的延时来释放CPU
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected.")