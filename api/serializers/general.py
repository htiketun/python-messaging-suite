from rest_framework import serializers

class SyncMessagesSerializer(serializers.Serializer):
    messages = serializers.JSONField()

class SyncToDoListSerializer(serializers.Serializer):
    todos_data = serializers.JSONField()