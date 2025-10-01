from fastapi import FastAPI, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime
import logging
import telegram_sync.sync_messages as sync_messages
import telegram_sync.sync_chats as sync_chats
import telegram_sync.session_manager as sm

logger = logging.getLogger(__name__)
from telegram_sync.realtime_api import (
    StartMonitoringRequest,
    StopMonitoringRequest,
    AddChatRequest,
    RemoveChatRequest,
    start_realtime_monitoring,
    stop_realtime_monitoring,
    get_monitoring_status,
    add_chat_to_monitoring,
    remove_chat_from_monitoring,
    websocket_endpoint
)
from telegram_sync.realtime_chat_list import chat_list_service

app = FastAPI(title="Telegram Messaging Suite API", version="1.0.0")

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

# Real-time messaging endpoints

@app.post("/realtime/start-monitoring/")
async def start_monitoring_endpoint(request: StartMonitoringRequest):
    """Start real-time message monitoring for a session"""
    return await start_realtime_monitoring(request)

@app.post("/realtime/stop-monitoring/")
async def stop_monitoring_endpoint(request: StopMonitoringRequest):
    """Stop real-time message monitoring for a session"""
    return await stop_realtime_monitoring(request)

@app.get("/realtime/status/")
async def monitoring_status_endpoint():
    """Get current real-time monitoring status"""
    return await get_monitoring_status()

@app.post("/realtime/add-chat/")
async def add_chat_endpoint(request: AddChatRequest):
    """Add a chat to monitoring for a session"""
    return await add_chat_to_monitoring(request)

@app.post("/realtime/remove-chat/")
async def remove_chat_endpoint(request: RemoveChatRequest):
    """Remove a chat from monitoring for a session"""
    return await remove_chat_from_monitoring(request)

# Chat List Real-time endpoints

@app.post("/realtime/start-chat-list-monitoring/")
async def start_chat_list_monitoring_endpoint(session_file: str):
    """Start real-time chat list monitoring for a session"""
    try:
        success = await chat_list_service.start_monitoring(session_file)
        
        if success:
            return {
                "status": "success",
                "message": f"Started chat list monitoring for session {session_file}",
                "session_file": session_file
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to start chat list monitoring for session {session_file}"
            }
    except Exception as e:
        logger.error(f"Error starting chat list monitoring: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/realtime/stop-chat-list-monitoring/")
async def stop_chat_list_monitoring_endpoint(session_file: str):
    """Stop real-time chat list monitoring for a session"""
    try:
        await chat_list_service.stop_monitoring(session_file)
        return {
            "status": "success",
            "message": f"Stopped chat list monitoring for session {session_file}",
            "session_file": session_file
        }
    except Exception as e:
        logger.error(f"Error stopping chat list monitoring: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/realtime/chat-list-status/")
async def chat_list_status_endpoint():
    """Get current chat list monitoring status"""
    try:
        active_sessions = await chat_list_service.get_active_sessions()
        return {
            "status": "success",
            "active_sessions": active_sessions,
            "websocket_connections": len(chat_list_service.websocket_connections),
            "total_sessions": len(active_sessions)
        }
    except Exception as e:
        logger.error(f"Error getting chat list status: {e}")
        return {"status": "error", "message": str(e)}

@app.websocket("/ws/messages")
async def websocket_messages_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time messages"""
    await websocket_endpoint(websocket)

@app.websocket("/ws/chat-list")
async def websocket_chat_list_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat list updates"""
    await websocket.accept()
    await chat_list_service.add_websocket(websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to real-time chat list stream",
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (like ping/heartbeat or requests)
                data = await websocket.receive_json()
                
                # Handle client requests
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif data.get("type") == "get_chat_list":
                    # Send current chat list for requested session
                    session_file = data.get("session_file")
                    if session_file and session_file in chat_list_service.chat_cache:
                        chat_data = chat_list_service.chat_cache[session_file]
                        await websocket.send_json({
                            "type": "chat_list_current",
                            "session_file": session_file,
                            "chats": chat_data.get("chats", []),
                            "last_updated": chat_data.get("last_updated"),
                            "timestamp": datetime.now().isoformat()
                        })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in chat list WebSocket communication: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info("Chat list WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Chat list WebSocket error: {e}")
    finally:
        await chat_list_service.remove_websocket(websocket)

# Example usage:
# Start monitoring:
# curl -X POST "http://localhost:8000/realtime/start-monitoring/" \
#   -H "Content-Type: application/json" \
#   -d '{"session_file": "path/to/session.session", "chat_ids": [123456, 789012]}'
#
# WebSocket connection:
# ws://localhost:8000/ws/messages
#
# Stop monitoring:
# curl -X POST "http://localhost:8000/realtime/stop-monitoring/" \
#   -H "Content-Type: application/json" \
#   -d '{"session_file": "path/to/session.session"}'