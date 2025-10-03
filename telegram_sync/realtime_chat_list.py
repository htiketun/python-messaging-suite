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
from telethon.tl.functions.users import GetFullUserRequest
from datetime import datetime
import telegram_sync.config as config
import telegram_sync.db as db
from telethon.tl.types import UserStatusEmpty, UserStatusOnline, UserStatusOffline, UserStatusRecently, UserStatusLastWeek, UserStatusLastMonth
from datetime import datetime, timedelta, timezone
import os
import re
from openai import OpenAI
import random

logger = logging.getLogger(__name__)

class RealtimeChatListService:
    def __init__(self):
        self.active_sessions: Dict[str, TelegramClient] = {}
        self.websocket_connections: Set = set()
        self.monitored_sessions: Dict[str, bool] = {}
        self.chat_cache: Dict[str, Dict] = {}  # session_file -> chat_data
        self.conn = None  # Database connection will be initialized as needed
       
    async def get_db_connection(self):
        """Get database connection (creates new connection each time for thread safety)"""
        return await db.get_db()
    
    def _normalize_session_path(self, session_file: str) -> str:
        """
        Normalize session file path to full absolute path.
        Handles various input formats like './sessions/file.session', 'file.session', etc.
        """
        # Remove leading './' if present
        if session_file.startswith('./'):
            session_file = session_file[2:]
        
        # If it's already a full path within sessions folder, use it as is
        if session_file.startswith('sessions/'):
            # Extract just the filename
            session_file = os.path.basename(session_file)
        
        # If it's just a filename, create full path
        if not os.path.isabs(session_file):
            session_file = os.path.join(config.SESSION_FOLDER, session_file)
        
        # Return absolute path
        return os.path.abspath(session_file)

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
            
            # Normalize the session file path
            normalized_session_path = self._normalize_session_path(session_file)
            logger.info(f"Normalized session path from '{session_file}' to '{normalized_session_path}'")
                
            client = TelegramClient(normalized_session_path, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
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
        
    async def sync_database(self, session_file: str) -> bool:
        """Manually sync database for a specific session"""
        if session_file not in self.active_sessions:
            logger.error(f"Session {session_file} is not being monitored")
            return False
            
        client = self.active_sessions[session_file]
        try:
            await self._load_initial_chat_list(session_file, client)
            logger.info(f"Database sync completed for session: {session_file}")
            return True
        except Exception as e:
            logger.error(f"Error syncing database for {session_file}: {e}")
            return False
        
    async def _load_initial_chat_list(self, session_file: str, client: TelegramClient):
        """Load and cache initial chat list with database storage"""
        conn = None
        try:
            # Get database connection
            conn = await self.get_db_connection()
            chats = []
            me = await client.get_me()
            telegram_account_id = me.id

            count = 0
            async for dialog in client.iter_dialogs():
                if dialog.is_user:
                    # Store chat in database
                    try:
                        if hasattr(dialog.entity, "status") and dialog.entity.status:
                            status = dialog.entity.status
                            last_seen = None
                            # Extract last seen/online status from entity.status if available
                            if hasattr(dialog.entity, "status") and dialog.entity.status:
                                status = dialog.entity.status
                                last_seen = self._get_user_status(status) 

                            chatPhoto = f"media/telegram_photo/{me.id}/{dialog.entity.id}_photo.jpg"
                            full_photo_url_chat = None
                            if os.path.exists(chatPhoto):
                                full_photo_url_chat = f"{chatPhoto}"
                            else:
                                photo_path = await client.download_profile_photo(dialog.entity, file=chatPhoto)
                                if photo_path and os.path.exists(photo_path):
                                    full_photo_url_chat = f"{chatPhoto}"

                            await db.upsert_chat(conn, telegram_account_id, dialog, last_seen=last_seen, full_photo_url=full_photo_url_chat)
                            if dialog.message:
                                await db.upsert_message(conn, telegram_account_id, dialog.id, dialog.message)
                    except Exception as db_error:
                        logger.warning(f"Database error for chat {dialog.id}: {db_error}")

                    # Format for WebSocket
                    chat_data = await self._format_chat_data(dialog, me.id)
                    chats.append(chat_data)
                    count += dialog.unread_count
            
            me_name = getattr(me, 'username ', 'Me')
            me_photo_filename = f"media/telegram_photo/{me.id}/{me_name}_photo.jpg"
            full_photo_url = None
            if os.path.exists(me_photo_filename):
                full_photo_url = f"{me_photo_filename}"
            else:
                me_photo_path = await client.download_profile_photo(me, file=me_photo_filename)
                if me_photo_path and os.path.exists(me_photo_path):
                    full_photo_url = f"{me_photo_filename}"
                    
            await db.upsert_telegram_account(conn, session_file, me, count, full_photo_url=full_photo_url)
                
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
            
            logger.info(f"Loaded {len(chats)} chats for session: {session_file}")
            
        except Exception as e:
            logger.error(f"Error loading initial chat list for {session_file}: {e}")
        finally:
            if conn:
                await conn.close()
            
    async def _format_chat_data(self, dialog, me_id: int) -> dict:
        """Format dialog data for broadcasting"""
        chat_data = await self.get_chat_data(dialog.id, me_id, message_limit=1)
        # entity = dialog.entity
        
        # # Get basic chat info
        # chat_data = {
        #     'id': dialog.id,
        #     'name': self._get_chat_name(entity),
        #     'type': self._get_chat_type(entity),
        #     'unread_count': dialog.unread_count,
        #     'is_pinned': dialog.pinned,
        #     'is_muted': dialog.archived,  # Using archived as muted indicator
        #     'last_message': None,
        #     'online_status': None,
        #     'photo_url': None
        # }
        
        # # Add last message info
        # if dialog.message:
        #     chat_data['last_message'] = {
        #         'id': dialog.message.id,
        #         'text': getattr(dialog.message, 'message', '') or '[Media]',
        #         'date': dialog.message.date.isoformat() if dialog.message.date else None,
        #         'from_me': dialog.message.sender_id == me_id
        #     }
            
        # # Add online status for users
        # if isinstance(entity, User) and hasattr(entity, 'status'):
        #     chat_data['online_status'] = self._get_user_status(entity.status)
            
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
            
    def _get_user_status(self, status, type = None) -> dict:

        if type == 'object':
            if hasattr(status, 'was_online'):
                return {
                    'type': 'offline',
                    'last_seen': status.was_online.isoformat()
                }
            elif hasattr(status, '__class__'):
                status_name = status.__class__.__name__
                if 'Online' in status_name:
                    return {'type': 'online', 'last_seen' : datetime.now(timezone.utc).isoformat()}
                elif 'Recently' in status_name:
                    return {'type': 'recently', 'last_seen' : (datetime.now(timezone.utc) - timedelta(minutes=(random.randint(1, 6)))).isoformat()}
                elif 'LastWeek' in status_name:
                    return {'type': 'last_week', 'last_seen' :  (datetime.now(timezone.utc) - timedelta(days={random.randint(1, 7)})).isoformat()}
                elif 'LastMonth' in status_name:
                    return {'type': 'last_month', 'last_seen' : (datetime.now(timezone.utc) - timedelta(days=random.randint(8, 30))).isoformat()}
            
            return {'type': 'unknown'}
        if isinstance(status, UserStatusEmpty):
            return None
        elif isinstance(status, UserStatusOnline):
            return datetime.now(timezone.utc).isoformat()
        elif isinstance(status, UserStatusOffline):
            return status.was_online.isoformat()
        elif isinstance(status, UserStatusRecently):
            # Approximate "recently" as a random time between 1 and 10 minutes ago
            minutes_ago = random.randint(1, 6)
            return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
        elif isinstance(status, UserStatusLastWeek):
            # Approximate "last week" as a random time between 1 and 7 days ago
            days_ago = random.randint(1, 7)
            return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        elif isinstance(status, UserStatusLastMonth):
            # Approximate "last month" as a random time between 8 and 30 days ago
            days_ago = random.randint(8, 30)
            return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        else:
            return None
    

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
                    'status': self._get_user_status(event.status, type='object') if hasattr(event, 'status') else None,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling user update: {e}")
                
        @client.on(events.NewMessage)
        async def handle_new_message(event):
            """Handle new messages that affect chat list"""
            conn = None
            try:
                if hasattr(event, 'message') and event.message:
                    chat_id = event.message.peer_id.user_id if hasattr(event.message.peer_id, 'user_id') else None
                    if not chat_id:
                        chat_id = event.message.peer_id.chat_id if hasattr(event.message.peer_id, 'chat_id') else None
                    if not chat_id:
                        chat_id = event.message.peer_id.channel_id if hasattr(event.message.peer_id, 'channel_id') else None
                        
                    if chat_id:
                        
                        # Update database with new message
                        try:
                            conn = await self.get_db_connection()
                            telegram_account_id = await db.get_telegram_account_id(conn, session_file)


                            if telegram_account_id:
                                await db.upsert_message(conn, telegram_account_id, chat_id, event.message)
                        except Exception as db_error:
                            logger.error(f"Database error for new message: {db_error}")
                        finally:
                            if conn:
                                await conn.close()
                        
                        # Broadcast to WebSocket clients
                        await self.broadcast_to_websockets({
                            'type': 'chat_list_update',
                            'session_file': session_file,
                            'chat_id': chat_id,
                            'last_message': {
                                'id': event.message.id,
                                'text': getattr(event.message, 'message', '') or '[Media]',
                                'date': event.message.date.isoformat() if event.message.date else None,
                                'from_me': event.message.sender_id == telegram_account_id
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

    async def get_chat_data(self, chat_id: int, telegram_account_id: int, include_messages: bool = True, message_limit: int = 50) -> dict:
        """
        Get chat data with last message and recent messages (similar to TelegramChatDetailView)
        
        Args:
            chat_id: The chat ID to retrieve
            telegram_account_id: The telegram account ID
            include_messages: Whether to include recent messages
            message_limit: Number of recent messages to include (default 50)
            
        Returns:
            dict: Chat data with last message and recent messages
        """
        conn = None
        try:
            conn = await self.get_db_connection()
            
            # Try to get chat with the provided ID first
            chat_data = await self._get_chat_by_id(conn, chat_id, telegram_account_id)
            
            # If not found, try with alternative ID (add/remove negative sign)
            if not chat_data:
                alt_chat_id = str(chat_id)[1:] if str(chat_id).startswith('-') else '-' + str(chat_id)
                try:
                    alt_chat_id = int(alt_chat_id)
                    chat_data = await self._get_chat_by_id(conn, alt_chat_id, telegram_account_id)
                except ValueError:
                    pass
            
            if not chat_data:
                return {'error': 'Chat not found', 'status': 'not_found'}
            
            # Convert row to dict
            result = dict(chat_data)
            
            if include_messages:
                # Get last message
                last_message = await self._get_last_message(conn, result['id'], telegram_account_id)
                result['last_message'] = dict(last_message) if last_message else None
                
                # Get recent messages
                messages = await self._get_recent_messages(conn, result['id'], telegram_account_id, message_limit)
                result['messages'] = [dict(msg) for msg in messages]
            else:
                result['last_message'] = None
                result['messages'] = []
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting chat data for chat_id {chat_id}: {e}")
            return {'error': str(e), 'status': 'error'}
        finally:
            if conn:
                await conn.close()
    
    async def _get_chat_by_id(self, conn, chat_id: int, telegram_account_id: int):
        """Get chat by ID and telegram account ID"""
        return await conn.fetchrow(
            """
            SELECT id, telegram_account_id, name, type, username, unread_count, 
                   photo, last_message_id, last_message_time, gender, age, 
                   last_seen, is_favorite, is_active
            FROM telegram_chats 
            WHERE id = $1 AND telegram_account_id = $2
            """,
            chat_id, telegram_account_id
        )
    
    async def _get_last_message(self, conn, chat_id: int, telegram_account_id: int):
        """Get the last message for a chat"""
        return await conn.fetchrow(
            """
            SELECT chat_id, telegram_account_id, message_id, sender_id, text, date
            FROM telegram_messages 
            WHERE chat_id = $1 AND telegram_account_id = $2
            ORDER BY date DESC 
            LIMIT 1
            """,
            chat_id, telegram_account_id
        )
    
    async def _get_recent_messages(self, conn, chat_id: int, telegram_account_id: int, limit: int = 50):
        """Get recent messages for a chat"""
        return await conn.fetch(
            """
            SELECT chat_id, telegram_account_id, message_id, sender_id, text, date
            FROM telegram_messages 
            WHERE chat_id = $1 AND telegram_account_id = $2
            ORDER BY date DESC 
            LIMIT $3
            """,
            chat_id, telegram_account_id, limit
        )

    def predict_gender_age(self, name: str, bio: str, dob: str) -> str:
        """
        Predict gender and age using OpenAI API
        Same logic as in sync_chats.py
        """
        openai_client = OpenAI(api_key="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")
        
        if dob:
            prompt = (
                f"Given the following information:\n"
                f"Name: {name}\n"
                f"Bio: {bio}\n"
                f"Date of Birth: {dob}\n"
                "Predict the most likely gender (male or female) and the exact age (not a range) based on the date of birth. "
                "Respond ONLY with a valid JSON object like this: {\"gender\": \"male\", \"age\": \"32\"} and nothing else. "
                "If you are unsure, make your best guess."
            )
        else:
            prompt = (
                f"Given the following information:\n"
                f"Name: {name}\n"
                f"Bio: {bio}\n"
                f"Date of Birth: {dob}\n"
                "Predict the most likely gender (male or female) and an age range e.g. '18-25', '25-35', '35-45', '45-55', '55-65', '65+'. "
                "Respond ONLY with a valid JSON object like this: {\"gender\": \"male\", \"age\": \"20-30\"} and nothing else. "
                "If you are unsure, make your best guess."
            )

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that predicts gender (male or female) and age range (like '20-30', '30-40', etc) from name, bio, and date of birth. Respond ONLY with a valid JSON object like {\"gender\": \"male\", \"age\": \"20-30\"} and nothing else. Never leave gender or age empty. If unsure, make your best guess."},
                    {"role": "user", "content": prompt}
                ]
            )

            result = response.choices[0].message.content.strip()
            match = re.search(r'\{.*\}', result)
            if match:
                return match.group(0)
            else:
                # Fallback if no JSON found
                genders = ["male", "female"]
                start_age = random.randint(18, 60)
                end_age = start_age + random.choice([3, 5, 8, 10])
                age_range = f"{start_age}-{end_age}"
                return json.dumps({
                    "gender": random.choice(genders),
                    "age": age_range
                })
        except Exception as e:
            logger.error(f"Error predicting gender/age: {e}")
            # Fallback response
            genders = ["male", "female"]
            start_age = random.randint(18, 60)
            end_age = start_age + random.choice([3, 5, 8, 10])
            age_range = f"{start_age}-{end_age}"
            return json.dumps({
                "gender": random.choice(genders),
                "age": age_range
            })

    async def get_or_predict_age_gender(self, chat_id: int, session_file: str) -> dict:
        """
        Get age and gender for a chat, predicting if not already set
        Based on the code pattern you provided
        """
        conn = None
        try:
            if session_file not in self.active_sessions:
                return {'error': 'Session not active', 'status': 'inactive'}
            
            client = self.active_sessions[session_file]
            conn = await self.get_db_connection()
            
            # Get telegram account ID
            telegram_account_id = await db.get_telegram_account_id(conn, session_file)
            
            # Check if age and gender already set
            already_set = await db.check_age_and_gender_already_set(conn, chat_id)
            
            if already_set:
                # Get existing age and gender
                existing_data = await db.get_age_and_gender_already_set(conn, chat_id)
                if existing_data:
                    return {
                        'status': 'success',
                        'chat_id': chat_id,
                        'gender': existing_data.get('gender'),
                        'age': existing_data.get('age'),
                        'source': 'database'
                    }
            
            # Need to predict - get user info
            try:
                entity = await client.get_entity(chat_id)
                if not hasattr(entity, 'first_name'):
                    return {'error': 'Not a user chat', 'status': 'invalid_chat_type'}
                
                name = entity.first_name or ""
                if hasattr(entity, 'last_name') and entity.last_name:
                    name += f" {entity.last_name}"
                
                # Try to get bio if available (requires GetFullUserRequest)
                bio = ""
                dob = ""
                
                if hasattr(entity, "username") and entity.username:
                    try:
                        full_user = await client(GetFullUserRequest(entity.username))
                        # Try to extract date of birth (dob) if available
                        if hasattr(full_user.full_user, "birthday") and full_user.full_user.birthday:
                            # birthday is a Birthday object with day, month, year
                            b = full_user.full_user.birthday
                            dob = f"{b.year:04d}-{b.month:02d}-{b.day:02d}"
                        bio = hasattr(full_user.full_user, "about") and full_user.full_user.about or ""
                    except Exception as e:
                        logger.warning(f"Could not fetch full user info for {entity.id}: {e}")

                # Predict gender and age
                prediction = self.predict_gender_age(name, bio, dob)
                logger.info(f"Prediction for {name} ({chat_id}): {prediction}")
                
                try:
                    pred_json = json.loads(prediction)
                    gender = pred_json.get("gender")
                    age = pred_json.get("age")
                    
                    # Update database with prediction
                    await conn.execute(
                        """
                        UPDATE telegram_chats 
                        SET gender = $1, age = $2
                        WHERE id = $3 AND telegram_account_id = $4
                        """,
                        gender, age, chat_id, telegram_account_id
                    )
                    
                    return {
                        'status': 'success',
                        'chat_id': chat_id,
                        'gender': gender,
                        'age': age,
                        'source': 'predicted',
                        'prediction_data': {
                            'name': name,
                            'bio': bio,
                            'dob': dob
                        }
                    }
                    
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON for prediction: {prediction}")
                    return {'error': 'Invalid prediction format', 'status': 'prediction_error'}
                    
            except Exception as e:
                logger.error(f"Error getting user entity for chat {chat_id}: {e}")
                return {'error': str(e), 'status': 'entity_error'}
                
        except Exception as e:
            logger.error(f"Error getting age/gender for chat {chat_id}: {e}")
            return {'error': str(e), 'status': 'error'}
        finally:
            if conn:
                await conn.close()

    async def bulk_predict_age_gender(self, session_file: str, force_update: bool = False) -> dict:
        """
        Bulk predict age and gender for all private chats in a session
        """
        conn = None
        try:
            if session_file not in self.active_sessions:
                return {'error': 'Session not active', 'status': 'inactive'}
            
            client = self.active_sessions[session_file]
            conn = await self.get_db_connection()
            
            # Get telegram account ID
            telegram_account_id = await db.get_telegram_account_id(conn, session_file)
            
            # Get all private chats that need prediction (including names)
            if force_update:
                chat_ids = await conn.fetch(
                    """
                    SELECT id, name FROM telegram_chats 
                    WHERE telegram_account_id = $1 AND type = 'private'
                    """,
                    telegram_account_id
                )
            else:
                chat_ids = await conn.fetch(
                    """
                    SELECT id, name FROM telegram_chats 
                    WHERE telegram_account_id = $1 AND type = 'private' 
                    AND (age IS NULL OR gender IS NULL)
                    """,
                    telegram_account_id
                )
            
            results = {
                'status': 'success',
                'session_file': session_file,
                'total_chats': len(chat_ids),
                'processed': 0,
                'updated': 0,
                'errors': 0,
                'details': []
            }
            
            for row in chat_ids:
                chat_id = row['id']
                chat_name = row['name'] or f"Chat {chat_id}"
                try:
                    result = await self.get_or_predict_age_gender(chat_id, session_file)
                    results['processed'] += 1
                    
                    if result.get('status') == 'success':
                        if result.get('source') == 'predicted':
                            results['updated'] += 1
                        results['details'].append({
                            'chat_id': chat_id,
                            'chat_name': chat_name,
                            'status': 'success',
                            'gender': result.get('gender'),
                            'age': result.get('age'),
                            'source': result.get('source')
                        })
                    else:
                        results['errors'] += 1
                        results['details'].append({
                            'chat_id': chat_id,
                            'chat_name': chat_name,
                            'status': 'error',
                            'error': result.get('error', 'Unknown error')
                        })
                        
                except Exception as e:
                    results['errors'] += 1
                    results['details'].append({
                        'chat_id': chat_id,
                        'chat_name': chat_name,
                        'status': 'error',
                        'error': str(e)
                    })
                    logger.error(f"Error processing chat {chat_id} ({chat_name}): {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk prediction: {e}")
            return {'error': str(e), 'status': 'error'}
        finally:
            if conn:
                await conn.close()

# Global instance
chat_list_service = RealtimeChatListService()