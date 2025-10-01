import os
import uuid
import asyncio
from typing import Optional, Dict, Any

try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError
    from telethon.tl.types import User
except ImportError:
    TelegramClient = None
    SessionPasswordNeededError = Exception
    PhoneCodeInvalidError = Exception
    PasswordHashInvalidError = Exception
    User = None

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model

# Import after telethon to avoid circular imports
def get_telegram_account_model():
    from api.models.telegram_account import TelegramAccount
    return TelegramAccount


class TelethonService:
    """Service for managing Telethon client instances and authentication"""
    
    def __init__(self):
        self.clients: Dict[str, Any] = {}
        self._session_folder = None
        self._api_id = None
        self._api_hash = None
    
    @property
    def session_folder(self):
        if self._session_folder is None:
            self._session_folder = getattr(settings, 'TELEGRAM_SESSION_FOLDER', 'sessions')
            # Ensure session folder exists
            os.makedirs(self._session_folder, exist_ok=True)
        return self._session_folder
    
    @property
    def api_id(self):
        if self._api_id is None:
            self._api_id = getattr(settings, 'TELEGRAM_API_ID')
        return self._api_id
    
    @property
    def api_hash(self):
        if self._api_hash is None:
            self._api_hash = getattr(settings, 'TELEGRAM_API_HASH')
        return self._api_hash
    
    def get_client(self, account_id: str):
        """Get or create a Telegram client instance"""
        if TelegramClient is None:
            raise ImportError("Telethon is not installed. Please install it with: pip install telethon")
        
        if account_id not in self.clients:
            session_path = os.path.join(self.session_folder, f"{account_id}.session")
            client = TelegramClient(session_path, self.api_id, self.api_hash)
            self.clients[account_id] = client
        return self.clients[account_id]
    
    async def start_client(self, account_id: str, phone=None):
        """Start a Telegram client"""
        client = self.get_client(account_id)
        if not client.is_connected():
            if phone:
                # Start with phone for authentication
                await client.start(phone=phone)
            else:
                # Just connect without starting authentication
                await client.connect()
        return client
    
    async def get_me(self, account_id: str):
        """Get current user info if logged in"""
        try:
            client = self.get_client(account_id)
            if not client.is_connected():
                await client.connect()
            
            if await client.is_user_authorized():
                return await client.get_me()
            return None
        except Exception:
            return None
    
    async def send_code_request(self, account_id: str, phone: str) -> Dict[str, Any]:
        """Send SMS code to phone number"""
        try:
            client = self.get_client(account_id)
            if not client.is_connected():
                await client.connect()
            
            result = await client.send_code_request(phone)
            
            # Cache phone number for this account
            cache_key = f"{account_id}_phone_{phone}"
            cache.set(cache_key, phone, 3600)  # 1 hour
            
            return {
                'success': True,
                'phone_code_hash': result.phone_code_hash
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def sign_in(self, account_id: str, phone: str, code: str, phone_code_hash: str) -> Dict[str, Any]:
        """Sign in with phone number and SMS code"""
        try:
            client = self.get_client(account_id)
            if not client.is_connected():
                await client.connect()
                
            user = await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            
            return {
                'success': True,
                'user': user,
                'needs_password': False
            }
        except SessionPasswordNeededError:
            return {
                'success': True,
                'needs_password': True
            }
        except PhoneCodeInvalidError:
            return {
                'success': False,
                'error': 'Invalid verification code'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def sign_in_with_password(self, account_id: str, password: str) -> Dict[str, Any]:
        """Sign in with 2FA password"""
        try:
            client = self.get_client(account_id)
            if not client.is_connected():
                await client.connect()
                
            user = await client.sign_in(password=password)
            
            return {
                'success': True,
                'user': user
            }
        except PasswordHashInvalidError:
            return {
                'success': False,
                'error': 'Invalid password'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def sign_up(self, account_id: str, phone: str, code: str, phone_code_hash: str, 
                     first_name: str, last_name: str = '') -> Dict[str, Any]:
        """Sign up new user"""
        try:
            client = await self.start_client(account_id)
            user = await client.sign_up(code, first_name, last_name, phone=phone, phone_code_hash=phone_code_hash)
            
            return {
                'success': True,
                'user': user
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def download_profile_photo(self, account_id: str, user) -> Optional[str]:
        """Download user profile photo"""
        try:
            client = self.get_client(account_id)
            if not client.is_connected():
                await client.connect()
                
            if user.photo:
                photo_dir = os.path.join(settings.MEDIA_ROOT, 'telegram_photo')
                os.makedirs(photo_dir, exist_ok=True)
                
                photo_path = await client.download_profile_photo(
                    user, 
                    file=photo_dir
                )
                
                if photo_path:
                    return os.path.basename(photo_path)
            return None
        except Exception:
            return None
    
    def update_telegram_account(self, account_id: str, user, django_user, phone: str):
        """Update or create TelegramAccount in database"""
        # Download profile photo if available
        photo_filename = None
        if user.photo:
            try:
                loop = asyncio.get_event_loop()
                photo_filename = loop.run_until_complete(
                    self.download_profile_photo(account_id, user)
                )
            except:
                pass
        
        TelegramAccount = get_telegram_account_model()
        telegram_account, created = TelegramAccount.objects.update_or_create(
            user=django_user,
            phone=phone,
            defaults={
                'session_file': account_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'photo': photo_filename,
            }
        )
        
        return telegram_account
    
    async def disconnect_client(self, account_id: str):
        """Disconnect a client"""
        if account_id in self.clients:
            client = self.clients[account_id]
            if client.is_connected():
                await client.disconnect()
            del self.clients[account_id]
    
    def generate_account_id(self) -> str:
        """Generate unique account ID"""
        return str(uuid.uuid4())


# Global instance
telethon_service = TelethonService()