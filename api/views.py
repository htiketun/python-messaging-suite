from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer
from rest_framework.permissions import AllowAny

class HelloWorld(APIView):
    def get(self, request):
        return Response({"message": "Hello, World!"})

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

class CustomTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]