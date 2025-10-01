"""
Real-time Chat List Service

This service monitors Telegram chats for real-time updates and broadcasts
changes to connected WebSocket clients. It tracks:
- New chats
- Chat metadata changes (name, photo, online status)
- Unread message counts
- Last seen status updates
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Optional
from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel
from datetime import datetime
import telegram_sync.config as config
import telegram_sync.db as db

logger = logging.getLogger(__name__)

class RealtimeChatListService:
    def __init__(self):
        self.active_sessions: Dict[str, TelegramClient] = {}
        self.websocket_connections: Set = set()
        self.monitored_sessions: Dict[str, bool] = {}
        self.chat_cache: Dict[str, Dict] = {}  # session_file -> chat_data
        
    async def add_websocket(self, websocket):
        """Add a WebSocket connection for broadcasting"""
        self.websocket_connections.add(websocket)
        logger.info(f"Added WebSocket connection. Total: {len(self.websocket_connections)}")
        
    async def remove_websocket(self, websocket):
        """Remove a WebSocket connection"""
        self.websocket_connections.discard(websocket)
        logger.info(f"Removed WebSocket connection. Total: {len(self.websocket_connections)}")
        
    async def broadcast_to_websockets(self, data: dict):
        """Broadcast data to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
            
        disconnected = set()
        for websocket in self.websocket_connections.copy():
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(websocket)
                
        # Remove disconnected WebSockets
        for ws in disconnected:
            self.websocket_connections.discard(ws)
            
    async def start_monitoring(self, session_file: str) -> bool:
        """Start monitoring a Telegram session for chat list updates"""
        try:
            if session_file in self.active_sessions:
                logger.info(f"Session {session_file} already being monitored")
                return True
                
            client = TelegramClient(session_file, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error(f"Session {session_file} is not authorized")
                await client.disconnect()
                return False
                
            self.active_sessions[session_file] = client
            self.monitored_sessions[session_file] = True
            
            # Load initial chat list
            await self._load_initial_chat_list(session_file, client)
            
            # Set up event handlers
            await self._setup_event_handlers(session_file, client)
            
            logger.info(f"Started monitoring chat list for session: {session_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring for {session_file}: {e}")
            return False
            
    async def stop_monitoring(self, session_file: str):
        """Stop monitoring a Telegram session"""
        if session_file in self.active_sessions:
            try:
                client = self.active_sessions[session_file]
                await client.disconnect()
                del self.active_sessions[session_file]
                self.monitored_sessions.pop(session_file, None)
                self.chat_cache.pop(session_file, None)
                logger.info(f"Stopped monitoring session: {session_file}")
            except Exception as e:
                logger.error(f"Error stopping monitoring for {session_file}: {e}")
                
    async def get_active_sessions(self) -> List[str]:
        """Get list of currently monitored sessions"""
        return list(self.active_sessions.keys())
        
    async def _load_initial_chat_list(self, session_file: str, client: TelegramClient):
        """Load and cache initial chat list"""
        try:
            chats = []
            me = await client.get_me()
            
            async for dialog in client.iter_dialogs():
                chat_data = await self._format_chat_data(dialog, me.id)
                chats.append(chat_data)
                
            self.chat_cache[session_file] = {
                'chats': chats,
                'last_updated': datetime.now().isoformat()
            }
            
            # Broadcast initial chat list to WebSocket clients
            await self.broadcast_to_websockets({
                'type': 'chat_list_initial',
                'session_file': session_file,
                'chats': chats,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error loading initial chat list for {session_file}: {e}")
            
    async def _format_chat_data(self, dialog, me_id: int) -> dict:
        """Format dialog data for broadcasting"""
        entity = dialog.entity
        
        # Get basic chat info
        chat_data = {
            'id': dialog.id,
            'name': self._get_chat_name(entity),
            'type': self._get_chat_type(entity),
            'unread_count': dialog.unread_count,
            'is_pinned': dialog.pinned,
            'is_muted': dialog.archived,  # Using archived as muted indicator
            'last_message': None,
            'online_status': None,
            'photo_url': None
        }
        
        # Add last message info
        if dialog.message:
            chat_data['last_message'] = {
                'id': dialog.message.id,
                'text': getattr(dialog.message, 'message', '') or '[Media]',
                'date': dialog.message.date.isoformat() if dialog.message.date else None,
                'from_me': dialog.message.sender_id == me_id
            }
            
        # Add online status for users
        if isinstance(entity, User) and hasattr(entity, 'status'):
            chat_data['online_status'] = self._get_user_status(entity.status)
            
        return chat_data
        
    def _get_chat_name(self, entity) -> str:
        """Get chat display name"""
        if isinstance(entity, User):
            if entity.first_name and entity.last_name:
                return f"{entity.first_name} {entity.last_name}"
            elif entity.first_name:
                return entity.first_name
            elif entity.username:
                return f"@{entity.username}"
            else:
                return "Unknown User"
        elif isinstance(entity, (Chat, Channel)):
            return entity.title or "Unknown Chat"
        else:
            return "Unknown"
            
    def _get_chat_type(self, entity) -> str:
        """Get chat type"""
        if isinstance(entity, User):
            return "user"
        elif isinstance(entity, Chat):
            return "group"
        elif isinstance(entity, Channel):
            return "channel" if entity.broadcast else "supergroup"
        else:
            return "unknown"
            
    def _get_user_status(self, status) -> dict:
        """Get user online status"""
        if hasattr(status, 'was_online'):
            return {
                'type': 'offline',
                'last_seen': status.was_online.isoformat()
            }
        elif hasattr(status, '__class__'):
            status_name = status.__class__.__name__
            if 'Online' in status_name:
                return {'type': 'online'}
            elif 'Recently' in status_name:
                return {'type': 'recently'}
            elif 'LastWeek' in status_name:
                return {'type': 'last_week'}
            elif 'LastMonth' in status_name:
                return {'type': 'last_month'}
        
        return {'type': 'unknown'}
        
    async def _setup_event_handlers(self, session_file: str, client: TelegramClient):
        """Set up Telethon event handlers for chat list updates"""
        
        @client.on(events.UserUpdate)
        async def handle_user_update(event):
            """Handle user status updates"""
            try:
                await self.broadcast_to_websockets({
                    'type': 'user_status_update',
                    'session_file': session_file,
                    'user_id': event.user_id,
                    'status': self._get_user_status(event.status) if hasattr(event, 'status') else None,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling user update: {e}")
                
        @client.on(events.NewMessage)
        async def handle_new_message(event):
            """Handle new messages that affect chat list"""
            try:
                if hasattr(event, 'message') and event.message:
                    chat_id = event.message.peer_id.user_id if hasattr(event.message.peer_id, 'user_id') else None
                    if not chat_id:
                        chat_id = event.message.peer_id.chat_id if hasattr(event.message.peer_id, 'chat_id') else None
                    if not chat_id:
                        chat_id = event.message.peer_id.channel_id if hasattr(event.message.peer_id, 'channel_id') else None
                        
                    if chat_id:
                        me = await client.get_me()
                        await self.broadcast_to_websockets({
                            'type': 'chat_list_update',
                            'session_file': session_file,
                            'chat_id': chat_id,
                            'last_message': {
                                'id': event.message.id,
                                'text': getattr(event.message, 'message', '') or '[Media]',
                                'date': event.message.date.isoformat() if event.message.date else None,
                                'from_me': event.message.sender_id == me.id
                            },
                            'timestamp': datetime.now().isoformat()
                        })
            except Exception as e:
                logger.error(f"Error handling new message for chat list: {e}")
                
        @client.on(events.MessageRead)
        async def handle_message_read(event):
            """Handle message read events that affect unread counts"""
            try:
                await self.broadcast_to_websockets({
                    'type': 'unread_count_update',
                    'session_file': session_file,
                    'chat_id': getattr(event, 'chat_id', None),
                    'max_id': getattr(event, 'max_id', None),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling message read: {e}")

# Global instance
chat_list_service = RealtimeChatListService()