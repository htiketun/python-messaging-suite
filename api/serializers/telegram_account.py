from rest_framework import serializers
from api.models.telegram_account import TelegramAccount
from api.models.user import User

class TelegramAccountSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = TelegramAccount
        fields = [
            'id', 'user', 'user_email', 'user_name', 'session_file', 
            'phone', 'username', 'first_name', 'last_name', 'photo', 
            'gender', 'is_active', 'unread_count', 'last_seen'
        ]
        extra_kwargs = {
            'user': {'required': False, 'allow_null': True}
        }

class TelegramAccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramAccount
        fields = [
            'user', 'session_file', 'phone', 'username', 
            'first_name', 'last_name', 'photo', 'gender', 'is_active'
        ]
        extra_kwargs = {
            'user': {'required': False, 'allow_null': True},
            'session_file': {'required': False, 'allow_null': True}
        }