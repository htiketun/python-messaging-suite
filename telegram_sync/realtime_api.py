from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from telegram_sync.realtime_messages import realtime_service

logger = logging.getLogger(__name__)

class StartMonitoringRequest(BaseModel):
    session_file: str
    chat_ids: Optional[List[int]] = None

class StopMonitoringRequest(BaseModel):
    session_file: str

class AddChatRequest(BaseModel):
    session_file: str
    chat_id: int

class RemoveChatRequest(BaseModel):
    session_file: str
    chat_id: int

async def start_realtime_monitoring(request: StartMonitoringRequest):
    """Start real-time message monitoring for a session"""
    try:
        success = await realtime_service.start_monitoring(
            request.session_file, 
            request.chat_ids
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Started monitoring for session {request.session_file}",
                "session_file": request.session_file,
                "monitored_chats": await realtime_service.get_monitored_chats(request.session_file)
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to start monitoring for session {request.session_file}"
            )
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def stop_realtime_monitoring(request: StopMonitoringRequest):
    """Stop real-time message monitoring for a session"""
    try:
        await realtime_service.stop_monitoring(request.session_file)
        return {
            "status": "success",
            "message": f"Stopped monitoring for session {request.session_file}",
            "session_file": request.session_file
        }
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_monitoring_status():
    """Get current monitoring status"""
    try:
        active_sessions = await realtime_service.get_active_sessions()
        status_data = {}
        
        for session in active_sessions:
            monitored_chats = await realtime_service.get_monitored_chats(session)
            status_data[session] = {
                "active": True,
                "monitored_chats": monitored_chats,
                "chat_count": len(monitored_chats)
            }
        
        return {
            "status": "success",
            "active_sessions": len(active_sessions),
            "websocket_connections": len(realtime_service.websocket_connections),
            "sessions": status_data
        }
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def add_chat_to_monitoring(request: AddChatRequest):
    """Add a chat to monitoring for a session"""
    try:
        await realtime_service.add_chat_to_monitoring(request.session_file, request.chat_id)
        return {
            "status": "success",
            "message": f"Added chat {request.chat_id} to monitoring",
            "session_file": request.session_file,
            "chat_id": request.chat_id
        }
    except Exception as e:
        logger.error(f"Error adding chat to monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def remove_chat_from_monitoring(request: RemoveChatRequest):
    """Remove a chat from monitoring for a session"""
    try:
        await realtime_service.remove_chat_from_monitoring(request.session_file, request.chat_id)
        return {
            "status": "success",
            "message": f"Removed chat {request.chat_id} from monitoring",
            "session_file": request.session_file,
            "chat_id": request.chat_id
        }
    except Exception as e:
        logger.error(f"Error removing chat from monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time messages"""
    await websocket.accept()
    await realtime_service.add_websocket(websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to real-time message stream",
            "timestamp": "now"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (like ping/heartbeat)
                data = await websocket.receive_json()
                
                # Handle client requests
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": "now"
                    })
                elif data.get("type") == "get_status":
                    active_sessions = await realtime_service.get_active_sessions()
                    await websocket.send_json({
                        "type": "status",
                        "active_sessions": active_sessions,
                        "connection_count": len(realtime_service.websocket_connections)
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket communication: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await realtime_service.remove_websocket(websocket)