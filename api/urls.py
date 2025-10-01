from django.urls import path
from .views import (
    HelloWorld, 
    RegisterView, 
    CustomTokenObtainPairView, 
    LogoutView, 
    ProfileView, 
    UpdateProfileView, 
    ChangePasswordView,
    SyncSavedMessages,
    GetSyncedSavedMessages,
    SyncToDoList,
    GetSyncedToDoList,
    csrf_cookie
)
from api.views.telegram_chat import (
    TelegramAccountListView,
    TelegramChatListView,
    TelegramChatDetailView,
    TelegramChatMessagesView,
    SendMessageView,
)
from api.views.telegram_auth import (
    StartLoginView,
    CheckLoginView,
    SubmitPhoneView,
    SubmitCodeView,
    SubmitPasswordView,
    SubmitSignupView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('hello/', HelloWorld.as_view()),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='get_profile'),
    path('profile/update/', UpdateProfileView.as_view(), name='update_profile'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('sync-saved-messages/', SyncSavedMessages.as_view(), name='saved-messages-sync'),
    path('get-synced-saved-messages/', GetSyncedSavedMessages.as_view(), name='saved-messages-index'),
    path('sync-todo-list/', SyncToDoList.as_view(), name='todo-list-sync'),
    path('get-synced-todo-list/', GetSyncedToDoList.as_view(), name='todo-list-index'),
    path('telegram/accounts/', TelegramAccountListView.as_view(), name='telegram-account-list'),
    path('chats/', TelegramChatListView.as_view(), name='chat-list'),
    path('chats/<str:id>/', TelegramChatDetailView.as_view(), name='chat-detail'),
    path('chats/<str:id>/messages/', TelegramChatMessagesView.as_view(), name='chat-messages'),
    path('chats/<str:id>/send/', SendMessageView.as_view(), name='chat-send-message'),
    path('sanctum/csrf-cookie/', csrf_cookie),  # Dummy endpoint for CSRF cookie

    # Telegram Authentication endpoints
    path('auth/telegram/start-login/', StartLoginView.as_view(), name='telegram-start-login'),
    path('auth/telegram/check-login/', CheckLoginView.as_view(), name='telegram-check-login'),
    path('auth/telegram/submit-phone/', SubmitPhoneView.as_view(), name='telegram-submit-phone'),
    path('auth/telegram/submit-code/', SubmitCodeView.as_view(), name='telegram-submit-code'),
    path('auth/telegram/submit-password/', SubmitPasswordView.as_view(), name='telegram-submit-password'),
    path('auth/telegram/submit-signup/', SubmitSignupView.as_view(), name='telegram-submit-signup'),
]