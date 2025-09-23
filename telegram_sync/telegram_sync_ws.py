from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import telegram_sync.sync_messages as sync_messages
import telegram_sync.sync_chats as sync_chats
import telegram_sync.session_manager as sm

app = FastAPI()

class SyncRequest(BaseModel):
    session_file: str = None
    chat_id: int = None
    direction: str = "new"
    limit: int = 100

@app.websocket("/ws/telegram-chats/")
async def websocket_sync_chats(ws: WebSocket):
    await ws.accept()
    try:
        data = await ws.receive_json()
        session_file = data.get("session_file")
        session_files = [session_file] if session_file else None
        session_files = sm.get_session_files(session_files)
        await ws.send_json({"status": "progress", "message": "Starting chat sync..."})
        await sync_chats.main(session_files=session_files)
        await ws.send_json({"status": "success", "message": "Chats synced successfully"})
    except Exception as e:
        await ws.send_json({"status": "error", "detail": str(e)})
    finally:
        await ws.close()

@app.websocket("/ws/telegram-messages/")
async def websocket_sync_messages(ws: WebSocket):
    await ws.accept()
    try:
        data = await ws.receive_json()
        session_file = data.get("session_file")
        chat_id = data.get("chat_id")
        direction = data.get("direction", "new")
        limit = data.get("limit", 100)
        session_files = [session_file] if session_file else None
        session_files = sm.get_session_files(session_files)
        await ws.send_json({"status": "progress", "message": "Starting message sync..."})
        await sync_messages.main(
            full_sync=False,
            session_files=session_files,
            chat_id=chat_id,
            direction=direction,
            limit=limit
        )
        await ws.send_json({"status": "success", "message": "Messages synced successfully"})
    except Exception as e:
        await ws.send_json({"status": "error", "detail": str(e)})
    finally:
        await ws.close()

# Connect to ws://localhost:8000/ws/telegram-chats/ (as a WebSocket client)
# Send: {"session_file": "path/to/session.session"} (or {} for all)
# Connect to ws://localhost:8000/ws/telegram-messages/
# Send: {"session_file": "...", "chat_id": 123, "direction": "new", "limit": 100}