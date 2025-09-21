from django.db import models

class PasswordResetToken(models.Model):
    email = models.EmailField(primary_key=True)
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email