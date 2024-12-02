from rest_framework.views import APIView
from rest_framework.response import Response

class HelloWorld(APIView):
    def get(self, request):
        return Response({"message": "Hello, World!"})# Commit 67: 2024-12-02T11:29:36
