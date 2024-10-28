from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from api.models import TelegramAccount
from api.serializers import TelegramAccountSerializer
import os
import json

User = get_user_model()

class AdminTelegramAccountManagementView(APIView):
    """Admin view for managing Telegram accounts and session files"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get all Telegram accounts with user information"""
        accounts = TelegramAccount.objects.select_related('user').all()
        data = []
        
        for account in accounts:
            account_data = {
                'id': account.id,
                'phone': account.phone,
                'username': account.username,
                'first_name': account.first_name,
                'last_name': account.last_name,
                'session_file': account.session_file,
                'is_active': account.is_active,
                'user': {
                    'id': account.user.id if account.user else None,
                    'email': account.user.email if account.user else None,
                    'name': account.user.name if account.user else None,
                } if account.user else None,
                'session_file_exists': self._check_session_file_exists(account.session_file)
            }
            data.append(account_data)
            
        return Response({
            'success': True,
            'accounts': data
        })
    
    def post(self, request):
        """Create new Telegram account or upload session file"""
        if 'session_file' in request.FILES:
            return self._handle_session_upload(request)
        else:
            return self._create_account(request)
    
    def put(self, request, account_id):
        """Update Telegram account or assign to user"""
        account = get_object_or_404(TelegramAccount, id=account_id)
        
        # Handle user assignment
        if 'user_id' in request.data:
            user_id = request.data['user_id']
            if user_id:
                user = get_object_or_404(User, id=user_id)
                account.user = user
            else:
                account.user = None
            account.save()
            
            return Response({
                'success': True,
                'message': 'User assignment updated successfully',
                'account': {
                    'id': account.id,
                    'phone': account.phone,
                    'username': account.username,
                    'user': {
                        'id': account.user.id if account.user else None,
                        'email': account.user.email if account.user else None,
                        'name': account.user.name if account.user else None,
                    } if account.user else None
                }
            })
        
        # Handle other updates
        serializer = TelegramAccountSerializer(account, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Account updated successfully',
                'account': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, account_id):
        """Delete Telegram account and its session file"""
        account = get_object_or_404(TelegramAccount, id=account_id)
        
        # Remove session file if exists
        if account.session_file:
            session_path = os.path.join('sessions', account.session_file)
            if os.path.exists(session_path):
                os.remove(session_path)
        
        account.delete()
        
        return Response({
            'success': True,
            'message': 'Account and session file deleted successfully'
        })
    
    def _handle_session_upload(self, request):
        """Handle session file upload"""
        session_file = request.FILES['session_file']
        phone = request.data.get('phone', '')
        username = request.data.get('username', '')
        
        # Validate file extension
        if not session_file.name.endswith('.session'):
            return Response({
                'success': False,
                'error': 'Invalid file type. Only .session files are allowed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create sessions directory if it doesn't exist
        sessions_dir = 'sessions'
        os.makedirs(sessions_dir, exist_ok=True)
        
        # Generate filename
        base_name = phone or username or 'unknown'
        filename = f"session_{base_name}.session"
        file_path = os.path.join(sessions_dir, filename)
        
        # Save file
        with open(file_path, 'wb+') as destination:
            for chunk in session_file.chunks():
                destination.write(chunk)
        
        # Create or update TelegramAccount
        account_data = {
            'session_file': filename,
            'phone': phone,
            'username': username,
            'first_name': request.data.get('first_name', ''),
            'last_name': request.data.get('last_name', ''),
            'is_active': True
        }
        
        # Assign to user if specified
        user_id = request.data.get('user_id')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            account_data['user'] = user
        
        # Check if account already exists
        existing_account = None
        if phone:
            existing_account = TelegramAccount.objects.filter(phone=phone).first()
        elif username:
            existing_account = TelegramAccount.objects.filter(username=username).first()
        
        if existing_account:
            # Update existing account
            for key, value in account_data.items():
                setattr(existing_account, key, value)
            existing_account.save()
            account = existing_account
        else:
            # Create new account
            account = TelegramAccount.objects.create(**account_data)
        
        return Response({
            'success': True,
            'message': 'Session file uploaded successfully',
            'account': {
                'id': account.id,
                'phone': account.phone,
                'username': account.username,
                'session_file': account.session_file,
                'user': {
                    'id': account.user.id if account.user else None,
                    'email': account.user.email if account.user else None,
                    'name': account.user.name if account.user else None,
                } if account.user else None
            }
        })
    
    def _create_account(self, request):
        """Create new Telegram account"""
        serializer = TelegramAccountSerializer(data=request.data)
        if serializer.is_valid():
            account = serializer.save()
            return Response({
                'success': True,
                'message': 'Account created successfully',
                'account': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _check_session_file_exists(self, session_file):
        """Check if session file exists on filesystem"""
        if not session_file:
            return False
        session_path = os.path.join('sessions', session_file)
        return os.path.exists(session_path)

class AdminUsersListView(APIView):
    """Get list of all users for admin assignment"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        users = User.objects.all()
        data = []
        
        for user in users:
            # Count assigned Telegram accounts
            telegram_accounts_count = TelegramAccount.objects.filter(user=user).count()
            
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'telegram_accounts_count': telegram_accounts_count
            }
            data.append(user_data)
        
        return Response({
            'success': True,
            'users': data
        })

class AdminSessionFileView(APIView):
    """Manage session files"""
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser]
    
    def post(self, request):
        """Upload session file without creating account"""
        if 'session_file' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No session file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session_file = request.FILES['session_file']
        custom_name = request.data.get('filename', '')
        
        # Validate file extension
        if not session_file.name.endswith('.session'):
            return Response({
                'success': False,
                'error': 'Invalid file type. Only .session files are allowed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create sessions directory if it doesn't exist
        sessions_dir = 'sessions'
        os.makedirs(sessions_dir, exist_ok=True)
        
        # Use custom name if provided, otherwise use original filename
        filename = custom_name if custom_name.endswith('.session') else session_file.name
        file_path = os.path.join(sessions_dir, filename)
        
        # Save file
        with open(file_path, 'wb+') as destination:
            for chunk in session_file.chunks():
                destination.write(chunk)
        
        return Response({
            'success': True,
            'message': 'Session file uploaded successfully',
            'filename': filename,
            'path': file_path
        })
    
    def get(self, request):
        """List all session files"""
        sessions_dir = 'sessions'
        if not os.path.exists(sessions_dir):
            return Response({
                'success': True,
                'files': []
            })
        
        files = []
        for filename in os.listdir(sessions_dir):
            if filename.endswith('.session'):
                file_path = os.path.join(sessions_dir, filename)
                file_stat = os.stat(file_path)
                
                # Check if this session file is assigned to any account
                assigned_account = TelegramAccount.objects.filter(session_file=filename).first()
                
                files.append({
                    'filename': filename,
                    'size': file_stat.st_size,
                    'modified': file_stat.st_mtime,
                    'assigned_to_account': {
                        'id': assigned_account.id,
                        'phone': assigned_account.phone,
                        'username': assigned_account.username,
                        'user': {
                            'id': assigned_account.user.id if assigned_account.user else None,
                            'email': assigned_account.user.email if assigned_account.user else None,
                            'name': assigned_account.user.name if assigned_account.user else None,
                        } if assigned_account and assigned_account.user else None
                    } if assigned_account else None
                })
        
        return Response({
            'success': True,
            'files': files
        })
    
    def delete(self, request, filename):
        """Delete a session file"""
        sessions_dir = 'sessions'
        file_path = os.path.join(sessions_dir, filename)
        
        if not os.path.exists(file_path):
            return Response({
                'success': False,
                'error': 'Session file not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if file is assigned to any account
        assigned_account = TelegramAccount.objects.filter(session_file=filename).first()
        if assigned_account:
            return Response({
                'success': False,
                'error': f'Cannot delete session file. It is assigned to account: {assigned_account.phone or assigned_account.username}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        os.remove(file_path)
        
        return Response({
            'success': True,
            'message': 'Session file deleted successfully'
        })

class AdminDashboardView(APIView):
    """Admin dashboard with statistics"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        total_users = User.objects.count()
        total_accounts = TelegramAccount.objects.count()
        active_accounts = TelegramAccount.objects.filter(is_active=True).count()
        unassigned_accounts = TelegramAccount.objects.filter(user__isnull=True).count()
        
        # Count session files
        sessions_dir = 'sessions'
        session_files_count = 0
        if os.path.exists(sessions_dir):
            session_files_count = len([f for f in os.listdir(sessions_dir) if f.endswith('.session')])
        
        return Response({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_telegram_accounts': total_accounts,
                'active_telegram_accounts': active_accounts,
                'unassigned_accounts': unassigned_accounts,
                'session_files_count': session_files_count,
            }
        })


class AssignedUsersView(APIView):
    """Return users who have been assigned Telegram accounts"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Get users who have at least one Telegram account assigned
        assigned_users = User.objects.filter(
            telegramaccount__isnull=False
        ).distinct().prefetch_related('telegramaccount_set')
        
        data = []
        for user in assigned_users:
            # Get all Telegram accounts for this user
            telegram_accounts = user.telegramaccount_set.all()
            accounts_data = []
            
            for account in telegram_accounts:
                account_info = {
                    'id': account.id,
                    'phone': account.phone,
                    'username': account.username,
                    'first_name': account.first_name,
                    'last_name': account.last_name,
                    'session_file': account.session_file,
                    'is_active': account.is_active,
                    'session_file_exists': self._check_session_file_exists(account.session_file),
                    'last_seen': account.last_seen,
                    'unread_count': account.unread_count
                }
                accounts_data.append(account_info)
            
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'telegram_accounts_count': len(accounts_data),
                'telegram_accounts': accounts_data
            }
            data.append(user_data)
        
        return Response({
            'success': True,
            'assigned_users': data,
            'total_assigned_users': len(data)
        })
    
    def _check_session_file_exists(self, session_file):
        """Check if session file exists on disk"""
        if not session_file:
            return False
        session_path = os.path.join('sessions', session_file)
        return os.path.exists(session_path)


class AssignedUsersSimpleView(APIView):
    """Return basic information about users who have been assigned Telegram accounts"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Get users who have at least one Telegram account assigned
        assigned_users = User.objects.filter(
            telegramaccount__isnull=False
        ).distinct()
        
        data = []
        for user in assigned_users:
            # Count accounts for this user
            accounts_count = TelegramAccount.objects.filter(user=user).count()
            active_accounts_count = TelegramAccount.objects.filter(user=user, is_active=True).count()
            
            user_data = {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'telegram_accounts_count': accounts_count,
                'active_accounts_count': active_accounts_count
            }
            data.append(user_data)
        
        return Response({
            'success': True,
            'assigned_users': data,
            'total_assigned_users': len(data)
        })# Commit 17: 2024-08-07T11:09:28
# Commit 52: 2024-10-28T08:15:44
