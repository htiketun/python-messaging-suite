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
