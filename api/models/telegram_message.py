from django.db import models

from .telegram_chat import TelegramChat
class TelegramMessage(models.Model):
    chat_id = models.BigIntegerField(db_index=True)
    session = models.TextField(db_index=True)
    message_id = models.BigIntegerField(db_index=True)
    sender_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    text = models.TextField(null=True, blank=True)
    date = models.DateTimeField()

    class Meta:
        unique_together = (('chat_id', 'session', 'message_id'),)
        db_table = 'telegram_messages'