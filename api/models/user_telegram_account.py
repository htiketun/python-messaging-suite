from django.db import models
from .user import User
from .telegram_account import TelegramAccount

class UserTelegramAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    telegram_account = models.ForeignKey(TelegramAccount, on_delete=models.CASCADE)

    class Meta:
        db_table = 'user_telegram_accounts'