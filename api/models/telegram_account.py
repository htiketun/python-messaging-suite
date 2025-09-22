from django.db import models
class TelegramAccount(models.Model):
    session_file = models.CharField(max_length=255, primary_key=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    username = models.CharField(max_length=150, blank=True, null=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    photo = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'telegram_accounts'