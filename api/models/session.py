from django.db import models
from .user import User

class Session(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    payload = models.TextField()
    last_activity = models.IntegerField(db_index=True)