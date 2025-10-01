from django.db import models
from django.conf import settings

class TelegramAccount(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_file = models.CharField(max_length=100, db_index=True)
    phone = models.CharField(max_length=20, blank=True, null=True, db_index=True, unique=True)
    username = models.CharField(max_length=150, blank=True, null=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    photo = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True, null=True)
    unread_count = models.IntegerField(default=0)
    last_seen = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'telegram_accounts'