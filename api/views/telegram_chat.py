from api.models.telegram_account import TelegramAccount
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from api.models.telegram_chat import TelegramChat
from api.models.telegram_message import TelegramMessage
from api.serializers.telegram_chat import TelegramChatSerializer
from api.serializers.telegram_message import TelegramMessageSerializer
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from telethon.sync import TelegramClient
import telegram_sync.config as config
import asyncio
import os

class TelegramChatListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TelegramChatSerializer

    def get_queryset(self): 
        telegram_account_id = self.request.query_params.get('telegram_account_id')
        if not telegram_account_id:
            return TelegramChat.objects.none()
        return TelegramChat.objects.filter(
            telegram_account_id=telegram_account_id
        ).order_by('last_message_time')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
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

    def get_object(self):
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
        chat_id = self.kwargs['id']
        return TelegramMessage.objects.filter(chat_id=chat_id).order_by('-date')

class SendMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, id):
        text = request.data.get('text')
        telegram_account_id = int(request.data.get('telegram_account_id'))
        if not text:
            return Response({"error": "Text is required."}, status=status.HTTP_400_BAD_REQUEST)

        telegram_account = get_object_or_404(TelegramAccount, id=telegram_account_id)
        session_file = os.path.join(config.SESSION_FOLDER, telegram_account.session_file)
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
