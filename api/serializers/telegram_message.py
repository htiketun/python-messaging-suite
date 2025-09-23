from rest_framework import serializers
from api.models.telegram_message import TelegramMessage

class TelegramMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramMessage
        fields = '__all__'