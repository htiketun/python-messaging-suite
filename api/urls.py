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
    GetSyncedToDoList 
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
]