from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'email_verified_at')
        
class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('name', 'email')