# backend/app/api/v1/endpoints/ws.py

import asyncio
import json
import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path
from app.core.config import CELERY_BROKER_URL
from app.tasks import run_backtest_task

router = APIRouter()

@router.websocket("/backtest/{backtest_id}")
async def websocket_endpoint(websocket: WebSocket, backtest_id: int = Path(...)):
    print(f"--- WS: Connection accepted for backtest_id: {backtest_id} ---")
    await websocket.accept()
    redis_client = redis.from_url(CELERY_BROKER_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    channel = f"backtest_{backtest_id}"
    print(f"--- WS: Subscribing to Redis channel: {channel} ---")
    await pubsub.subscribe(channel)

    # Task to listen for client messages (like a start command)
    async def client_listener(ws: WebSocket):
        try:
            while True:
                data = await ws.receive_text()
                print(f"--- WS: Received message from client: {data} ---")
                message = json.loads(data)
                if message.get('action') == 'start':
                    print(f"--- WS: Received 'start' command. Triggering Celery task for backtest_id: {backtest_id} ---")
                    run_backtest_task.delay(backtest_id)
        except WebSocketDisconnect:
            print(f"--- WS: Client disconnected from client_listener. ---")
        except Exception as e:
            print(f"--- WS: Error in client_listener: {e} ---")


    # Task to listen for Redis messages and forward them to the client
    async def redis_listener(ws: WebSocket, ps: redis.client.PubSub):
        try:
            while True:
                message = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    print(f"--- WS: Received message from Redis on channel {channel}: {message['data']} ---")
                    await ws.send_text(message['data'])
                await asyncio.sleep(0.01)
        except WebSocketDisconnect:
            print(f"--- WS: Client disconnected from redis_listener. ---")
        except Exception as e:
            print(f"--- WS: Error in redis_listener: {e} ---")

    # Run both listeners concurrently
    client_task = asyncio.create_task(client_listener(websocket))
    redis_task = asyncio.create_task(redis_listener(websocket, pubsub))

    try:
        done, pending = await asyncio.wait(
            [client_task, redis_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        print(f"--- WS: Closing connection for backtest {backtest_id}. Unsubscribing and closing Redis. ---")
        await pubsub.unsubscribe(channel)
        await redis_client.close()