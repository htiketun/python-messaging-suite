import asyncio
import json
import logging
import os
from typing import Dict, Set, List, Optional
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel
import telegram_sync.config as config
import telegram_sync.db as db

logger = logging.getLogger(__name__)

class RealTimeMessageService:
    """Service for handling real-time Telegram messages via WebSocket"""
    
    def __init__(self):
        # Remove active_sessions - we'll use the shared client from chat_list_service
        self.websocket_connections: Set = set()
        self.monitored_chats: Dict[str, Set[int]] = {}  # session_file -> set of chat_ids
        self.running = False
        self.message_handlers: Dict[str, List] = {}  # session_file -> list of handlers
        

    async def start_monitoring(self, session_file: str, chat_ids: Optional[List[int]] = None):
        """Start monitoring messages for a session - uses shared client from chat_list_service"""
        try:
            # Import here to avoid circular imports
            from .realtime_chat_list import chat_list_service
            
            # Check if the session is already being monitored by chat_list_service
            if session_file not in chat_list_service.active_sessions:
                logger.error(f"Session {session_file} is not active in chat_list_service. Start chat monitoring first.")
                return False
            
            # Use the existing client from chat_list_service
            client = chat_list_service.active_sessions[session_file]
            
            if session_file in self.monitored_chats:
                logger.info(f"Message monitoring for session {session_file} is already active")
                return True
            
            # Set up monitored chats
            if chat_ids:
                self.monitored_chats[session_file] = set(chat_ids)
            else:
                # Monitor all chats if none specified
                conn = await db.get_db()
                telegram_account_id = await db.get_telegram_account_id(conn, session_file)
                all_chat_ids = await db.get_chat_ids_from_telegram_chat(conn, telegram_account_id)
                self.monitored_chats[session_file] = set(all_chat_ids) if all_chat_ids else set()
                await conn.close()
            
            # Store event handlers for this session so we can remove them later
            self.message_handlers[session_file] = []
            
            # Add event handler for new messages
            @client.on(events.NewMessage)
            async def handle_new_message(event):
                await self._handle_new_message(session_file, event)
            
            # Add event handler for edited messages  
            @client.on(events.MessageEdited)
            async def handle_edited_message(event):
                await self._handle_edited_message(session_file, event)
            
            # Store handlers for cleanup
            self.message_handlers[session_file] = [handle_new_message, handle_edited_message]
            
            logger.info(f"Started real-time message monitoring for session {session_file} with {len(self.monitored_chats[session_file])} chats")
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring for session {session_file}: {e}")
            return False
    
    async def stop_monitoring(self, session_file: str):
        """Stop monitoring messages for a session"""
        try:
            # Remove event handlers (note: in Telethon, handlers are automatically cleaned up when client disconnects)
            if session_file in self.message_handlers:
                del self.message_handlers[session_file]
                
            if session_file in self.monitored_chats:
                del self.monitored_chats[session_file]
                
            logger.info(f"Stopped message monitoring for session {session_file}")
            
        except Exception as e:
            logger.error(f"Error stopping message monitoring for session {session_file}: {e}")
    
    async def add_websocket(self, websocket):
        """Add a WebSocket connection"""
        self.websocket_connections.add(websocket)
        logger.info(f"Added WebSocket connection. Total connections: {len(self.websocket_connections)}")
    
    async def remove_websocket(self, websocket):
        """Remove a WebSocket connection"""
        self.websocket_connections.discard(websocket)
        logger.info(f"Removed WebSocket connection. Total connections: {len(self.websocket_connections)}")
    
    async def _handle_new_message(self, session_file: str, event):
        """Handle new message event"""
        try:
            # Check if we should monitor this chat
            chat_id = event.chat_id
            if session_file in self.monitored_chats:
                if self.monitored_chats[session_file] and chat_id not in self.monitored_chats[session_file]:
                    return  # Skip this chat
            
            # Get message details
            message = event.message
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            # Save to database
            conn = await db.get_db()
            telegram_account_id = await db.get_telegram_account_id(conn, session_file)
            if telegram_account_id:
                await db.upsert_message(conn, telegram_account_id, chat_id, message)
                await db.set_last_synced_message(conn, telegram_account_id, chat_id, message.id, message.date, newest=True)
            await conn.close()
            
            # Prepare message data for WebSocket
            message_data = {
                'type': 'new_message',
                'session_file': session_file,
                'chat_id': chat_id,
                'message_id': message.id,
                'date': message.date.isoformat() if message.date else None,
                'text': message.text or '',
                'sender': {
                    'id': sender.id if sender else None,
                    'first_name': getattr(sender, 'first_name', ''),
                    'last_name': getattr(sender, 'last_name', ''),
                    'username': getattr(sender, 'username', ''),
                },
                'chat': {
                    'id': chat.id,
                    'title': getattr(chat, 'title', ''),
                    'username': getattr(chat, 'username', ''),
                    'type': 'user' if isinstance(chat, User) else 'group' if isinstance(chat, Chat) else 'channel'
                },
                'media': bool(message.media),
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to all WebSocket connections
            await self._broadcast_to_websockets(message_data)
            
            logger.info(f"Processed new message {message.id} from chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error handling new message: {e}")
    
    async def _handle_edited_message(self, session_file: str, event):
        """Handle edited message event"""
        try:
            # Similar to new message but mark as edited
            chat_id = event.chat_id
            if session_file in self.monitored_chats:
                if self.monitored_chats[session_file] and chat_id not in self.monitored_chats[session_file]:
                    return
            
            message = event.message
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            # Update in database
            conn = await db.get_db()
            telegram_account_id = await db.get_telegram_account_id(conn, session_file)
            if telegram_account_id:
                await db.upsert_message(conn, telegram_account_id, chat_id, message)
            await conn.close()
            
            # Prepare edited message data
            message_data = {
                'type': 'message_edited',
                'session_file': session_file,
                'chat_id': chat_id,
                'message_id': message.id,
                'date': message.date.isoformat() if message.date else None,
                'text': message.text or '',
                'sender': {
                    'id': sender.id if sender else None,
                    'first_name': getattr(sender, 'first_name', ''),
                    'last_name': getattr(sender, 'last_name', ''),
                    'username': getattr(sender, 'username', ''),
                },
                'timestamp': datetime.now().isoformat()
            }
            
            await self._broadcast_to_websockets(message_data)
            
            logger.info(f"Processed edited message {message.id} from chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error handling edited message: {e}")
    
    async def _broadcast_to_websockets(self, data: dict):
        """Broadcast data to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message = json.dumps(data)
        disconnected = set()
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected WebSocket connections
        for websocket in disconnected:
            self.websocket_connections.discard(websocket)
    
    async def get_active_sessions(self) -> List[str]:
        """Get list of active monitoring sessions"""
        return list(self.monitored_chats.keys())
    
    async def get_monitored_chats(self, session_file: str) -> List[int]:
        """Get list of monitored chats for a session"""
        return list(self.monitored_chats.get(session_file, set()))
    
    async def add_chat_to_monitoring(self, session_file: str, chat_id: int):
        """Add a chat to monitoring for a session"""
        if session_file not in self.monitored_chats:
            self.monitored_chats[session_file] = set()
        self.monitored_chats[session_file].add(chat_id)
        logger.info(f"Added chat {chat_id} to monitoring for session {session_file}")
    
    async def remove_chat_from_monitoring(self, session_file: str, chat_id: int):
        """Remove a chat from monitoring for a session"""
        if session_file in self.monitored_chats:
            self.monitored_chats[session_file].discard(chat_id)
            logger.info(f"Removed chat {chat_id} from monitoring for session {session_file}")
    
    async def shutdown(self):
        """Shutdown the service and clean up handlers"""
        logger.info("Shutting down real-time message service...")
        
        for session_file in list(self.monitored_chats.keys()):
            await self.stop_monitoring(session_file)
        
        self.websocket_connections.clear()
        logger.info("Real-time message service shutdown complete")

# Global instance
realtime_service = RealTimeMessageService()