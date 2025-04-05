from api.models.telegram_account import TelegramAccount
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from api.models.telegram_chat import TelegramChat
from api.models.telegram_message import TelegramMessage
from api.serializers.telegram_account import TelegramAccountSerializer
from api.serializers.telegram_chat import TelegramChatSerializer
from api.serializers.telegram_message import TelegramMessageSerializer
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from telethon.sync import TelegramClient
import telegram_sync.config as config
import asyncio
import os
class TelegramAccountListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None  # No serializer needed for listing accounts

    def post(self, request, *args, **kwargs):
        accounts = TelegramAccount.objects.select_related('user').all().values('id', 'session_file', 'phone', 'username', 'first_name', 'last_name', 'photo', 'unread_count', 'is_active', 'last_seen')
        return Response(list(accounts), status=status.HTTP_200_OK)


class UserTelegramAccountsView(APIView):
    """Get Telegram accounts assigned to the currently logged-in user"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Return Telegram accounts assigned to the current user"""
        user = request.user
        
        # Get accounts assigned to the current user
        accounts = TelegramAccount.objects.filter(user=user).select_related('user')
        
        # Use serializer for consistent data structure
        serializer = TelegramAccountSerializer(accounts, many=True)
        account_data = serializer.data
        
        # Add session file existence check for each account
        for i, account in enumerate(accounts):
            session_file_exists = False
            if account.session_file:
                session_path = os.path.join('sessions', account.session_file)
                session_file_exists = os.path.exists(session_path)
            account_data[i]['session_file_exists'] = session_file_exists
        
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'is_active': user.is_active,
            },
            'telegram_accounts': account_data,
            'total_accounts': len(account_data),
            'active_accounts': len([acc for acc in account_data if acc['is_active']])
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """Alternative POST method for compatibility"""
        return self.get(request)
class TelegramChatListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TelegramChatSerializer

    def post(self, request):
        telegram_account_id = request.data.get('telegram_account_id')
        if not telegram_account_id:
            return Response([], status=status.HTTP_200_OK)
        queryset = TelegramChat.objects.filter(
            telegram_account_id=telegram_account_id
        ).filter(is_active=None).order_by('-last_message_id')
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        chat_ids = [chat['id'] for chat in data]
        last_messages = (
            TelegramMessage.objects.filter(chat_id__in=chat_ids)
            .order_by('chat_id', '-date')
            .distinct('chat_id')
        )
        last_message_map = {
            str(msg.chat_id): TelegramMessageSerializer(msg).data
            for msg in last_messages
        }

        for chat in data:
            chat['last_message'] = last_message_map.get(str(chat['id']))

        return Response(data)

class TelegramChatDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TelegramChatSerializer
    lookup_field = 'id'

    def post(self):
        chat_id = self.kwargs.get(self.lookup_field)
        try:
            return TelegramChat.objects.get(id=chat_id)
        except TelegramChat.DoesNotExist:
            alt_id = str(chat_id)[1:] if str(chat_id).startswith('-') else '-' + str(chat_id)
            return get_object_or_404(TelegramChat, id=alt_id)

    def get_last_message(self, chat):
        return TelegramMessage.objects.filter(chat_id=chat.id).order_by('-date').first()

    def get_messages(self, chat):
        return TelegramMessage.objects.filter(chat_id=chat.id).order_by('-date')[:50]

    def retrieve(self, request, *args, **kwargs):
        chat = self.get_object()
        serializer = self.get_serializer(chat)
        data = serializer.data
        last_message = self.get_last_message(chat)
        data['last_message'] = TelegramMessageSerializer(last_message).data if last_message else None
        messages = self.get_messages(chat)
        data['messages'] = TelegramMessageSerializer(messages, many=True).data
        return Response(data)

class TelegramMessagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class TelegramChatMessagesView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TelegramMessageSerializer
    pagination_class = TelegramMessagePagination

    def get_queryset(self):
        chat_id = self.kwargs.get('id')
        return TelegramMessage.objects.filter(chat_id=chat_id).order_by('-date')

    def post(self, request, id):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class SendMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, id):
        text = request.data.get('text')
        session_file = request.data.get('session_file')
        session_file = os.path.join(config.SESSION_FOLDER, session_file)
        api_id = config.TELEGRAM_API_ID
        api_hash = config.TELEGRAM_API_HASH

        async def send_message():
            async with TelegramClient(session_file, api_id, api_hash) as client:
                await client.send_message(int(id), text)

        try:
            asyncio.run(send_message())
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"status": "sent", "chat_id": id, "text": text}, status=status.HTTP_200_OK)
# Commit 94: 2025-02-03T15:15:34
# Commit 120: 2025-04-05T11:54:44
