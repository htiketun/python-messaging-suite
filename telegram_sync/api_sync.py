from fastapi import FastAPI, BackgroundTasks, Query
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

@app.post("/telegram-chats/")
async def sync_chats_api(session_file: str = None):
    """
    Trigger Telegram chat sync. Optionally provide a session file.
    """
    session_files = [session_file] if session_file else None
    session_files = sm.get_session_files(session_files)
    try:
        await sync_chats.main(session_files=session_files)
        return {"status": "success", "message": "Chats synced successfully"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# curl -X POST "http://localhost:8000/telegram-chats/?session_file=path/to/session.session"
# curl -X POST "http://localhost:8000/telegram-chats/"
@app.post("/telegram-messages/")
async def sync_messages_api(req: SyncRequest):
    session_files = [req.session_file] if req.session_file else None
    session_files = sm.get_session_files(session_files)
    # You may want to validate session_file path here!
    try:
        await sync_messages.main(
            full_sync=False,
            session_files=session_files,
            chat_id=req.chat_id,
            direction=req.direction,
            limit=req.limit
        )
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
    
#     curl -X POST http://localhost:8000/sync-messages/ \
#   -H "Content-Type: application/json" \
#   -d '{"session_file": "path/to/session.session", "chat_id": 123456, "direction": "new", "limit": 100}'