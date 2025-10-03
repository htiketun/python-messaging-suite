from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime
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

async def handle_send_message(websocket: WebSocket, data: dict):
    """Handle sending a message through WebSocket"""
    try:
        # Extract message data
        chat_id = data.get("chat_id")
        text = data.get("text")
        session_file = data.get("session_file")
        temp_id = data.get("temp_id")
        
        if not all([chat_id, session_file]) or not text or not text.strip():
            await websocket.send_json({
                "type": "message_send_error",
                "chat_id": chat_id,
                "temp_id": temp_id,
                "error": "Missing required fields: chat_id, text, session_file or empty message"
            })
            return
        
        # Clean the text
        text = text.strip()
        
        # Import here to avoid circular imports
        from .realtime_chat_list import chat_list_service
        
        # Check if session is active
        if session_file not in chat_list_service.active_sessions:
            await websocket.send_json({
                "type": "message_send_error",
                "chat_id": chat_id,
                "temp_id": temp_id,
                "error": f"Session {session_file} is not active. Start chat monitoring first."
            })
            return
        
        # Get the Telegram client
        client = chat_list_service.active_sessions[session_file]
        
        # Send the message via Telegram
        try:
            logger.info(f"Sending message via Telegram to chat_id={chat_id}, text='{text[:50]}...'")
            sent_message = await client.send_message(int(chat_id), text)
            
            # Store the sent message in database
            conn = None
            try:
                import telegram_sync.db as db
                conn = await db.get_db()
                
                # Get telegram account ID
                telegram_account_id = await db.get_telegram_account_id(conn, session_file)
                
                # Store the sent message in database
                await db.upsert_message(conn, telegram_account_id, int(chat_id), sent_message)
                
                # Update chat's last message information
                await db.set_last_synced_message(conn, telegram_account_id, int(chat_id), 
                                                sent_message.id, sent_message.date, newest=True)
                
                # Update chat's last message in telegram_chats table
                await conn.execute(
                    """
                    UPDATE telegram_chats 
                    SET last_message_id = $1, last_message_time = $2
                    WHERE id = $3 AND telegram_account_id = $4
                    """,
                    sent_message.id,
                    sent_message.date.astimezone(tz=None).replace(tzinfo=None) if sent_message.date and sent_message.date.tzinfo else sent_message.date,
                    int(chat_id),
                    telegram_account_id
                )
                
                logger.info(f"Message stored in database: chat_id={chat_id}, message_id={sent_message.id}")
                
            except Exception as db_error:
                logger.error(f"Error storing message in database: {db_error}")
                # Continue execution even if database storage fails
            finally:
                if conn:
                    try:
                        await conn.close()
                    except Exception as close_error:
                        logger.warning(f"Error closing database connection: {close_error}")
            
            # Confirm message was sent successfully to the sender
            await websocket.send_json({
                "type": "message_sent",
                "chat_id": chat_id,
                "temp_id": temp_id,
                "message_id": sent_message.id,
                "text": text,
                "date": sent_message.date.isoformat() if sent_message.date else None,
                "success": True
            })
            
            # Broadcast the sent message to all other connected clients (for multi-device sync)
            me = await client.get_me()
            await broadcast_new_message({
                "type": "new_message",
                "chat_id": chat_id,
                "message_id": sent_message.id,
                "text": text,
                "date": sent_message.date.isoformat() if sent_message.date else None,
                "sender": {
                    "id": me.id,
                    "first_name": getattr(me, 'first_name', ''),
                    "last_name": getattr(me, 'last_name', ''),
                    "username": getattr(me, 'username', ''),
                },
                "session_file": session_file,
                "timestamp": datetime.now().isoformat()
            }, exclude_websocket=websocket)  # Exclude the sender's WebSocket
            
            logger.info(f"Message sent successfully via WebSocket: chat_id={chat_id}, message_id={sent_message.id}")
            
        except Exception as send_error:
            logger.error(f"Error sending message via Telegram: {send_error}")
            await websocket.send_json({
                "type": "message_send_error",
                "chat_id": chat_id,
                "temp_id": temp_id,
                "error": f"Failed to send message: {str(send_error)}"
            })
            
    except Exception as e:
        logger.error(f"Error in handle_send_message: {e}")
        await websocket.send_json({
            "type": "message_send_error",
            "chat_id": data.get("chat_id"),
            "temp_id": data.get("temp_id"),
            "error": f"Internal error: {str(e)}"
        })

async def handle_mark_messages_read(websocket: WebSocket, data: dict):
    """Handle marking all messages in a chat as read"""
    try:
        chat_id = data.get("chat_id")
        session_file = data.get("session_file")
        
        if not all([chat_id, session_file]):
            await websocket.send_json({
                "type": "read_update_error",
                "chat_id": chat_id,
                "error": "Missing required fields: chat_id, session_file"
            })
            return
        
        # Import here to avoid circular imports
        from .realtime_chat_list import chat_list_service
        
        # Check if session is active
        if session_file not in chat_list_service.active_sessions:
            await websocket.send_json({
                "type": "read_update_error",
                "chat_id": chat_id,
                "error": f"Session {session_file} is not active. Start chat monitoring first."
            })
            return
        
        # Get the Telegram client
        client = chat_list_service.active_sessions[session_file]
        try:
            # Mark all messages as read in Telegram
            await client.send_read_acknowledge(int(chat_id))
            
            # Update database
            from . import db
            conn = None
            try:
                conn = await db.get_db()
                telegram_account_id = await db.get_telegram_account_id(conn, session_file)
                await db.mark_messages_as_read(conn, telegram_account_id, int(chat_id))
            except Exception as db_error:
                logger.error(f"Database error marking messages as read: {db_error}")
            finally:
                if conn:
                    await conn.close()
            
            # Broadcast read update to all connected clients
            await broadcast_read_update({
                "type": "messages_marked_read",
                "chat_id": chat_id,
                "session_file": session_file,
                "timestamp": datetime.now().isoformat()
            })
            
            # Confirm to the requesting client
            await websocket.send_json({
                "type": "read_update_success",
                "chat_id": chat_id,
                "action": "mark_all_read",
                "success": True
            })
            
            logger.info(f"Marked all messages as read for chat {chat_id}")
            
        except Exception as read_error:
            logger.error(f"Error marking messages as read: {read_error}")
            await websocket.send_json({
                "type": "read_update_error",
                "chat_id": chat_id,
                "error": f"Failed to mark messages as read: {str(read_error)}"
            })
            
    except Exception as e:
        logger.error(f"Error in handle_mark_messages_read: {e}")
        await websocket.send_json({
            "type": "read_update_error",
            "chat_id": data.get("chat_id"),
            "error": f"Internal error: {str(e)}"
        })

async def handle_mark_message_read(websocket: WebSocket, data: dict):
    """Handle marking a specific message as read"""
    try:
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        session_file = data.get("session_file")
        
        if not all([chat_id, message_id, session_file]):
            await websocket.send_json({
                "type": "read_update_error",
                "chat_id": chat_id,
                "message_id": message_id,
                "error": "Missing required fields: chat_id, message_id, session_file"
            })
            return
        
        # Import here to avoid circular imports
        from .realtime_chat_list import chat_list_service
        
        # Check if session is active
        if session_file not in chat_list_service.active_sessions:
            await websocket.send_json({
                "type": "read_update_error",
                "chat_id": chat_id,
                "message_id": message_id,
                "error": f"Session {session_file} is not active. Start chat monitoring first."
            })
            return
        
        # Get the Telegram client
        client = chat_list_service.active_sessions[session_file]
        
        try:
            # Mark message as read in Telegram (up to this message ID)
            await client.send_read_acknowledge(int(chat_id), max_id=int(message_id))
            
            # Update database
            from . import db
            conn = None
            try:
                conn = await db.get_db()
                telegram_account_id = await db.get_telegram_account_id(conn, session_file)
                await db.mark_message_as_read(conn, telegram_account_id, int(chat_id), int(message_id))
            except Exception as db_error:
                logger.error(f"Database error marking message as read: {db_error}")
            finally:
                if conn:
                    await conn.close()
            
            # Broadcast read update to all connected clients
            await broadcast_read_update({
                "type": "message_read_update",
                "chat_id": chat_id,
                "message_id": message_id,
                "session_file": session_file,
                "status": "read",
                "timestamp": datetime.now().isoformat()
            })
            
            # Confirm to the requesting client
            await websocket.send_json({
                "type": "read_update_success",
                "chat_id": chat_id,
                "message_id": message_id,
                "action": "mark_message_read",
                "success": True
            })
            
            logger.info(f"Marked message {message_id} as read in chat {chat_id}")
            
        except Exception as read_error:
            logger.error(f"Error marking message as read: {read_error}")
            await websocket.send_json({
                "type": "read_update_error",
                "chat_id": chat_id,
                "message_id": message_id,
                "error": f"Failed to mark message as read: {str(read_error)}"
            })
            
    except Exception as e:
        logger.error(f"Error in handle_mark_message_read: {e}")
        await websocket.send_json({
            "type": "read_update_error",
            "chat_id": data.get("chat_id"),
            "message_id": data.get("message_id"),
            "error": f"Internal error: {str(e)}"
        })

async def broadcast_read_update(data: dict):
    """Broadcast read status updates to all connected WebSocket clients"""
    try:
        # Broadcast to all WebSocket connections in the realtime service
        if realtime_service.websocket_connections:
            disconnected = set()
            for websocket in realtime_service.websocket_connections:
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    logger.warning(f"Failed to send read update to WebSocket: {e}")
                    disconnected.add(websocket)
            
            # Remove disconnected WebSocket connections
            for websocket in disconnected:
                realtime_service.websocket_connections.discard(websocket)
                
    except Exception as e:
        logger.error(f"Error broadcasting read update: {e}")

async def broadcast_new_message(data: dict, exclude_websocket=None):
    """Broadcast new message to all connected WebSocket clients except the sender"""
    try:
        # Broadcast to all WebSocket connections in the realtime service
        if realtime_service.websocket_connections:
            disconnected = set()
            for websocket in realtime_service.websocket_connections:
                # Skip the sender's WebSocket to avoid duplicate messages
                if exclude_websocket and websocket == exclude_websocket:
                    continue
                    
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    logger.warning(f"Failed to send new message to WebSocket: {e}")
                    disconnected.add(websocket)
            
            # Remove disconnected WebSocket connections
            for websocket in disconnected:
                realtime_service.websocket_connections.discard(websocket)
                
    except Exception as e:
        logger.error(f"Error broadcasting new message: {e}")

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
                elif data.get("type") == "send_message":
                    # Handle sending message via WebSocket
                    await handle_send_message(websocket, data)
                elif data.get("type") == "mark_messages_read":
                    # Handle marking all messages as read
                    await handle_mark_messages_read(websocket, data)
                elif data.get("type") == "mark_message_read":
                    # Handle marking specific message as read
                    await handle_mark_message_read(websocket, data)
                    
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