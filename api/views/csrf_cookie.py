from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

@ensure_csrf_cookie
def csrf_cookie(request):
    # This will set the csrftoken cookie
    return JsonResponse({"detail": "CSRF cookie set"})