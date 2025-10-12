from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from django.core.files.storage import default_storage
import os
import json
from telegram_sync.telethon_service import telethon_service
import asyncio

@api_view(['POST'])
@permission_classes([IsAdminUser])
@parser_classes([MultiPartParser])
def upload_session_file(request):
    """
    Simple endpoint to upload session files
    """
    if 'session_file' not in request.FILES:
        return Response({
            'success': False,
            'error': 'No session file provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    session_file = request.FILES['session_file']
    
    # Validate file extension
    if not session_file.name.endswith('.session'):
        return Response({
            'success': False,
            'error': 'Invalid file type. Only .session files are allowed.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create sessions directory if it doesn't exist
    sessions_dir = 'sessions'
    os.makedirs(sessions_dir, exist_ok=True)
    
    # Use original filename or custom name if provided
    custom_name = request.data.get('filename', session_file.name)
    if not custom_name.endswith('.session'):
        custom_name += '.session'
    
    file_path = os.path.join(sessions_dir, custom_name)
    
    # Check if file already exists
    if os.path.exists(file_path):
        return Response({
            'success': False,
            'error': f'File {custom_name} already exists. Use a different name or delete the existing file first.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Save file
    try:
        with open(file_path, 'wb+') as destination:
            for chunk in session_file.chunks():
                destination.write(chunk)
        
        return Response({
            'success': True,
            'message': 'Session file uploaded successfully',
            'filename': custom_name,
            'path': file_path,
            'size': session_file.size
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to save file: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
# @permission_classes([IsAdminUser])
def list_session_files(request):
    """
    List all session files in the sessions directory
    """
    sessions_dir = 'tweb-sessions'
    
    if not os.path.exists(sessions_dir):
        return Response({
            'success': True,
            'files': [],
            'message': 'Sessions directory does not exist'
        })
    
    files = []
    async def get_status(account_id):
        user = await telethon_service.get_me(account_id)
        return user is not None

    try:
        session_files = [f for f in os.listdir(sessions_dir) if f.endswith('.session')]
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = [get_status(os.path.splitext(f)[0]) for f in session_files]
        results = loop.run_until_complete(asyncio.gather(*tasks))
        for idx, filename in enumerate(session_files):
            file_path = os.path.join(sessions_dir, filename)
            file_stat = os.stat(file_path)
            files.append({
                'filename': filename,
                'size': file_stat.st_size,
                'modified': file_stat.st_mtime,
                'path': file_path,
                'logged_in': results[idx]
            })
        return Response({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to list files: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_session_file(request, filename):
    """
    Delete a specific session file
    """
    sessions_dir = 'sessions'
    file_path = os.path.join(sessions_dir, filename)
    
    if not os.path.exists(file_path):
        return Response({
            'success': False,
            'error': 'Session file not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    try:
        os.remove(file_path)
        return Response({
            'success': True,
            'message': f'Session file {filename} deleted successfully'
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Failed to delete file: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)