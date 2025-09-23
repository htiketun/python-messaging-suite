from rest_framework import serializers
from api.models.telegram_chat import TelegramChat

class TelegramChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramChat
        fields = '__all__'