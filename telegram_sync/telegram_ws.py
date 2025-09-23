import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from telethon import TelegramClient, events
import telegram_sync.config as config
import os

app = FastAPI()
websockets = {}

@app.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    session_file: str = Query(...)
):
    await ws.accept()
    session_path = os.path.join("sessions", session_file)
    client = TelegramClient(session_path, config.API_ID, config.API_HASH)
    websockets[ws] = client

    @client.on(events.NewMessage)
    async def handler(event):
        text = event.raw_text
        try:
            await ws.send_text(text)
        except Exception:
            pass

    await client.start()
    client_task = asyncio.create_task(client.run_until_disconnected())

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await client.disconnect()
        client_task.cancel()
        websockets.pop(ws, None)

# uvicorn telegram_sync.telegram_ws:app --reload