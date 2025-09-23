from django.db import models

class TelegramMessage(models.Model):
    chat_id = models.BigIntegerField(db_index=True)
    telegram_account_id = models.BigIntegerField(db_index=True)
    message_id = models.BigIntegerField(db_index=True)
    sender_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    text = models.TextField(null=True, blank=True)
    date = models.DateTimeField()

    class Meta:
        unique_together = (('chat_id', 'telegram_account_id', 'message_id'),)
        db_table = 'telegram_messages'