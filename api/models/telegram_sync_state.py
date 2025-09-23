from django.db import models
from .telegram_chat import TelegramChat

class TelegramSyncState(models.Model):
    chat_id = models.BigIntegerField(db_index=True)
    telegram_account_id = models.BigIntegerField(db_index=True)
    last_message_id = models.BigIntegerField(db_index=True)
    oldest_message_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('chat_id', 'telegram_account_id')
        db_table = 'telegram_sync_state'