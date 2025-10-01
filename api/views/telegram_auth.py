import asyncio
import uuid
from typing import Dict, Any
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.contrib.auth import get_user_model
from telegram_sync.telethon_service import telethon_service
from api.models.telegram_account import TelegramAccount


class TelegramAuthMixin:
    """Mixin for common Telegram auth functionality"""
    
    def get_account_id(self, request) -> str:
        """Get or generate account ID"""
        account_id = request.data.get('account_id')
        if not account_id:
            account_id = str(uuid.uuid4().hex[:8])
        return account_id
    
    def get_phone_cache_key(self, account_id: str, user_id: int) -> str:
        """Get cache key for phone number"""
        return f"{account_id}_phone_number_{user_id}"
    
    def run_async(self, coro):
        """Run async coroutine"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


class StartLoginView(APIView, TelegramAuthMixin):
    """Start Telegram login process"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        account_id = self.get_account_id(request)

        # if account_id:
        #     # Check if already logged in
        #     me = self.run_async(telethon_service.get_me(account_id))
        #     if me:
        #         return Response({
        #         'status': 'logged_in',
        #         'account_id': account_id
        #     })
        
        # For now, we'll use phone-based login instead of QR
        # QR login implementation would require additional Telethon setup
        return Response({
            'status': 'need_phone',
            'account_id': account_id
        })


class CheckLoginView(APIView, TelegramAuthMixin):
    """Check login status"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        account_id = self.get_account_id(request)
        
        me = self.run_async(telethon_service.get_me(account_id))
        if me:
            return Response({
                'status': 'logged_in',
                'account_id': account_id
            })
        
        return Response({
            'status': 'not_logged_in',
            'account_id': account_id
        })


class SubmitPhoneView(APIView, TelegramAuthMixin):
    """Submit phone number for verification"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        account_id = self.get_account_id(request)
        phone = request.data.get('phone')
        
        if not phone:
            return Response({
                'status': 'error',
                'message': 'Phone number is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Send verification code
        result = self.run_async(telethon_service.send_code_request(account_id, phone))
        
        if result['success']:
            # Cache phone number and code hash
            phone_cache_key = self.get_phone_cache_key(account_id, request.user.id)
            cache.set(phone_cache_key, phone, 3600)  # 1 hour
            
            hash_cache_key = f"{account_id}_phone_code_hash_{request.user.id}"
            cache.set(hash_cache_key, result['phone_code_hash'], 3600)
            
            return Response({
                'status': 'code_sent',
                'account_id': account_id
            })
        else:
            return Response({
                'status': 'error',
                'message': result.get('error', 'Failed to send code'),
                'account_id': account_id
            }, status=status.HTTP_400_BAD_REQUEST)


class SubmitCodeView(APIView, TelegramAuthMixin):
    """Submit verification code"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        account_id = request.data.get('account_id')
        code = request.data.get('code')
        
        if not account_id or not code:
            return Response({
                'status': 'error',
                'message': 'Account ID and code are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get cached phone and hash
        phone_cache_key = self.get_phone_cache_key(account_id, request.user.id)
        phone = cache.get(phone_cache_key)
        
        hash_cache_key = f"{account_id}_phone_code_hash_{request.user.id}"
        phone_code_hash = cache.get(hash_cache_key)
        
        if not phone or not phone_code_hash:
            return Response({
                'status': 'error',
                'message': 'Session expired. Please start over.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to sign in
        result = self.run_async(telethon_service.sign_in(account_id, phone, code, phone_code_hash))
        
        if result['success']:
            if result.get('needs_password'):
                return Response({
                    'status': 'need_password',
                    'account_id': account_id
                })
            elif result.get('needs_signup'):
                return Response({
                    'status': 'need_signup',
                    'account_id': account_id
                })
            else:
                # Successfully logged in
                user = result['user']
                telethon_service.update_telegram_account(account_id, user, request.user, phone)
                
                return Response({
                    'status': 'logged_in',
                    'account_id': account_id
                })
        else:
            return Response({
                'status': 'error',
                'message': result.get('error', 'Invalid code'),
                'account_id': account_id
            }, status=status.HTTP_400_BAD_REQUEST)


class SubmitPasswordView(APIView, TelegramAuthMixin):
    """Submit 2FA password"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        account_id = request.data.get('account_id')
        password = request.data.get('password', '').strip()
        
        if not account_id or not password:
            return Response({
                'status': 'error',
                'message': 'Account ID and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get cached phone
        phone_cache_key = self.get_phone_cache_key(account_id, request.user.id)
        phone = cache.get(phone_cache_key)
        
        if not phone:
            return Response({
                'status': 'error',
                'message': 'Session expired. Please start over.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to sign in with password
        result = self.run_async(telethon_service.sign_in_with_password(account_id, password))
        
        if result['success']:
            user = result['user']
            telethon_service.update_telegram_account(account_id, user, request.user, phone)
            
            return Response({
                'status': 'logged_in',
                'account_id': account_id
            })
        else:
            return Response({
                'status': 'error',
                'message': result.get('error', 'Invalid password'),
                'account_id': account_id
            }, status=status.HTTP_400_BAD_REQUEST)


class SubmitSignupView(APIView, TelegramAuthMixin):
    """Submit signup information"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        account_id = request.data.get('account_id')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name', '')
        
        if not account_id or not first_name:
            return Response({
                'status': 'error',
                'message': 'Account ID and first name are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get cached data
        phone_cache_key = self.get_phone_cache_key(account_id, request.user.id)
        phone = cache.get(phone_cache_key)
        
        hash_cache_key = f"{account_id}_phone_code_hash_{request.user.id}"
        phone_code_hash = cache.get(hash_cache_key)
        
        code_cache_key = f"{account_id}_verification_code_{request.user.id}"
        code = cache.get(code_cache_key)
        
        if not phone or not phone_code_hash or not code:
            return Response({
                'status': 'error',
                'message': 'Session expired. Please start over.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to sign up
        result = self.run_async(telethon_service.sign_up(
            account_id, phone, code, phone_code_hash, first_name, last_name
        ))
        
        if result['success']:
            user = result['user']
            telethon_service.update_telegram_account(account_id, user, request.user, phone)
            
            return Response({
                'status': 'signed_up',
                'account_id': account_id
            })
        else:
            return Response({
                'status': 'error',
                'message': result.get('error', 'Signup failed'),
                'account_id': account_id
            }, status=status.HTTP_400_BAD_REQUEST)