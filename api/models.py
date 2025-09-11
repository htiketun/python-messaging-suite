# from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
# from django.db import models
# from django.utils import timezone

# class UserManager(BaseUserManager):
#     def create_user(self, email, name=None, password=None, **extra_fields):
#         if not email:
#             raise ValueError('Email is required')
#         email = self.normalize_email(email)
#         user = self.model(email=email, name=name, **extra_fields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user
    
#     def create_superuser(self, email, name=None, password=None, **extra_fields):
#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         return self.create_user(email, name, password, **extra_fields)

# class User(AbstractBaseUser, PermissionsMixin):
#     id = models.BigAutoField(primary_key=True)
#     name = models.CharField(max_length=255)
#     email = models.EmailField(unique=True)
#     email_verified_at = models.DateTimeField(null=True, blank=True)
#     password = models.CharField(max_length=128)
#     remember_token = models.CharField(max_length=255, null=True, blank=True)
#     is_active = models.BooleanField(default=True)
#     is_staff = models.BooleanField(default=False)
#     date_joined = models.DateTimeField(default=timezone.now)
#     # timestamps
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['name']

#     objects = UserManager()

#     def __str__(self):
#         return self.email

# class PasswordResetToken(models.Model):
#     email = models.EmailField(primary_key=True)
#     token = models.CharField(max_length=255)
#     created_at = models.DateTimeField(null=True, blank=True)

# class Session(models.Model):
#     id = models.CharField(primary_key=True, max_length=255)
#     user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
#     ip_address = models.CharField(max_length=45, null=True, blank=True)
#     user_agent = models.TextField(null=True, blank=True)
#     payload = models.TextField()
#     last_activity = models.IntegerField(db_index=True)

# Commit 12: 2024-07-26T18:22:16
# Commit 16: 2024-08-05T02:32:10
# Commit 22: 2024-08-19T04:09:19
# Commit 27: 2024-08-30T20:58:03
# Commit 31: 2024-09-09T05:37:25
# Commit 39: 2024-09-27T22:51:53
# Commit 53: 2024-10-30T16:54:30
# Commit 67: 2024-12-02T10:49:42
# Commit 93: 2025-02-01T07:41:53
# Commit 108: 2025-03-08T09:15:34
# Commit 112: 2025-03-17T18:09:47
# Commit 119: 2025-04-03T03:21:04
# Commit 123: 2025-04-12T12:26:46
# Commit 138: 2025-05-17T14:10:12
# Commit 146: 2025-06-05T07:17:29
# Commit 169: 2025-07-29T03:26:23
# Commit 176: 2025-08-14T12:23:04
# Commit 185: 2025-09-04T14:24:51
# Commit 192: 2025-09-20T23:22:52
# Commit 8: 2024-07-17T09:30:39
# Commit 12: 2024-07-26T18:16:40
# Commit 16: 2024-08-05T02:26:39
# Commit 34: 2024-09-16T05:22:41
# Commit 38: 2024-09-25T14:41:32
# Commit 25: 2024-08-26T04:19:04
# Commit 27: 2024-08-30T20:54:58
# Commit 39: 2024-09-27T22:29:41
# Commit 43: 2024-10-07T07:23:18
# Commit 45: 2024-10-11T23:42:40
# Commit 66: 2024-11-30T02:54:15
# Commit 107: 2025-03-06T01:53:44
# Commit 122: 2025-04-10T03:36:16
# Commit 125: 2025-04-17T04:37:24
# Commit 152: 2025-06-19T08:44:08
# Commit 159: 2025-07-05T17:21:22
# Commit 177: 2025-08-16T21:03:41
# Commit 178: 2025-08-19T04:41:49
# Commit 188: 2025-09-11T14:05:57
