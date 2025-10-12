from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import telegram_sync.sync_messages as sync_messages
import telegram_sync.sync_chats as sync_chats
import telegram_sync.session_manager as sm
import asyncio

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
        type = data.get("type")
        session_file = data.get("session_file")
        session_files = [session_file] if session_file else None
        session_files = sm.get_session_files(session_files)
        await ws.send_json({"status": "progress", "message": "Starting chat sync loop..."})

        while True:
            await sync_chats.main(session_files=session_files)
            await ws.send_json({"status": type, "message": "Chats synced successfully"})
            await asyncio.sleep(2)  # Wait 2 seconds before next sync

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"status": "error", "detail": str(e)})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass

@app.websocket("/ws/telegram-messages/")
async def websocket_sync_messages(ws: WebSocket):
    await ws.accept()
    try:
        data = await ws.receive_json()
        type = data.get("type")
        session_file = data.get("session_file")
        chat_id = data.get("chat_id")
        direction = data.get("direction", "new")
        limit = data.get("limit", 10)
        session_files = [session_file] if session_file else None
        session_files = sm.get_session_files(session_files)
        await ws.send_json({"status": "progress", "message": "Starting message sync loop..."})

        while True:
            await sync_messages.main(
                session_files=session_files,
                chat_id=chat_id,
                direction=direction,
                limit=limit
            )
            await ws.send_json({"status": type, "message": "Messages synced successfully"})
            await asyncio.sleep(2)  # Wait 2 seconds before next sync

    except WebSocketDisconnect:
        # Client disconnected, no further action needed
        pass
    except Exception as e:
        try:
            await ws.send_json({"status": "error", "detail": str(e)})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


# {"session_file":"session_909aed7e.session","chat_id":7127517690,"direction":"new","limit":10,"type":"messageSync"}


# Connect to ws://localhost:8000/ws/telegram-chats/ (as a WebSocket client)
# Send: {"session_file": "path/to/session.session"} (or {} for all)
# Connect to ws://localhost:8000/ws/telegram-messages/
# Send: {"session_file": "...", "chat_id": 123, "direction": "new", "limit": 100}