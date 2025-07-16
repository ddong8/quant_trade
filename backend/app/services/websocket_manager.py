# backend/app/services/websocket_manager.py
import json
from typing import List
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # 将Python字典转换为JSON字符串
        text_message = json.dumps(message)
        # 创建一个要移除的连接列表，避免在迭代时修改列表
        connections_to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_text(text_message)
            except WebSocketDisconnect:
                connections_to_remove.append(connection)
            except Exception as e:
                print(f"Error sending message to a client: {e}")
                connections_to_remove.append(connection)
        
        # 移除所有已断开的连接
        for connection in connections_to_remove:
            self.disconnect(connection)

manager = ConnectionManager()