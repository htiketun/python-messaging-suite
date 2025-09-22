from django.db import models

class TelegramChat(models.Model):
    id = models.BigIntegerField(primary_key=True, db_index=True)
    session = models.TextField(db_index=True)
    name = models.TextField()
    type = models.TextField()
    username = models.TextField(null=True, blank=True)
    oldest_message_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    oldest_message_time = models.DateTimeField(null=True, blank=True)
    last_message_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    last_message_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('id', 'session')
        db_table = 'telegram_chats'