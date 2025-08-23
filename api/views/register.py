from rest_framework import generics
from rest_framework.permissions import AllowAny
from ..serializers import RegisterSerializer

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]# Commit 180: 2025-08-23T21:29:42
