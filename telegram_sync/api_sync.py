from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7777", "http://127.0.0.1:7777", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/realtime/age-gender/{chat_id}")
async def get_age_gender_endpoint(chat_id: int, session_file: str):
    """
    Get or predict age and gender for a specific chat
    """
    try:
        
        # Check if session is being monitored
        if session_file not in chat_list_service.active_sessions:
            return {
                "status": "error",
                "message": f"Session {session_file} is not currently being monitored. Start monitoring first."
            }
        
        # Get age and gender data
        result = await chat_list_service.get_or_predict_age_gender(chat_id, session_file)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting age/gender: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "chat_id": chat_id,
            "session_file": session_file
        }

@app.post("/realtime/bulk-predict-age-gender/")
async def bulk_predict_age_gender_endpoint(
    session_file: str, 
    force_update: bool = False
):
    """
    Bulk predict age and gender for all private chats in a session
    
    Args:
        session_file: The session file to process
        force_update: If True, update even chats that already have age/gender data
    """
    try:
        
        # Check if session is being monitored
        if session_file not in chat_list_service.active_sessions:
            return {
                "status": "error",
                "message": f"Session {session_file} is not currently being monitored. Start monitoring first."
            }
        
        # Run bulk prediction
        result = await chat_list_service.bulk_predict_age_gender(session_file, force_update)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bulk prediction: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "session_file": session_file
        }

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
