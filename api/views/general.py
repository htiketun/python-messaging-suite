import os
import json
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..serializers import SyncMessagesSerializer, SyncToDoListSerializer
from .utils import ensure_dir_exists

PROJECT_ROOT = settings.BASE_DIR

class SyncSavedMessages(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SyncMessagesSerializer(data=request.data)
        if serializer.is_valid():
            messages = serializer.validated_data['messages']
            user_id = request.user.id
            dir_path = os.path.join(PROJECT_ROOT, 'saved_messages')
            ensure_dir_exists(dir_path)
            file_path = os.path.join(dir_path, f"{user_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f)
            return Response({"message": "Messages synced and saved successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

class GetSyncedSavedMessages(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        file_path = os.path.join(PROJECT_ROOT, 'saved_messages', f"{user_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        else:
            messages = []
        return Response({"messages": messages, "message": "Fetched synced messages successfully"}, status=status.HTTP_200_OK)

class SyncToDoList(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SyncToDoListSerializer(data=request.data)
        if serializer.is_valid():
            todos = serializer.validated_data['todos_data']
            user_id = request.user.id
            dir_path = os.path.join(PROJECT_ROOT, 'todo_list')
            ensure_dir_exists(dir_path)
            file_path = os.path.join(dir_path, f"{user_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(todos, f)
            return Response({"message": "To-Do list synced and saved successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class GetSyncedToDoList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        file_path = os.path.join(PROJECT_ROOT, 'todo_list', f"{user_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                todos = json.load(f)
        else:
            todos = ""
        return Response({"todos": todos, "message": "Fetched synced to-do list successfully"}, status=status.HTTP_200_OK)# Commit 113: 2025-03-20T02:51:50
# Commit 171: 2025-08-02T19:47:32
