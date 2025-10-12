from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.forms import ModelForm, FileField, Form, widgets, ValidationError
from django.utils.html import format_html
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from .models import User, TelegramAccount, TelegramChat, TelegramMessage
import os
import asyncio
import subprocess
import sys

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'name')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'name', 'is_active', 'is_staff', 'is_superuser')

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ['email', 'name', 'is_staff', 'is_active', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2'),
        }),
    )
    search_fields = ['email', 'name']
    ordering = ['email']

class TelegramAccountAdminForm(ModelForm):
    session_file_upload = FileField(required=False, help_text="Upload a new session file (.session)")
    
    class Meta:
        model = TelegramAccount
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        phone = cleaned_data.get('phone')
        
        # Validate that phone numbers are unique (if provided)
        if phone:
            existing_accounts = TelegramAccount.objects.filter(phone=phone)
            if self.instance and self.instance.pk:
                existing_accounts = existing_accounts.exclude(pk=self.instance.pk)
            
            if existing_accounts.exists():
                raise ValidationError(f"Another Telegram account with phone {phone} already exists.")
        
        # Check for user assignment limits (optional - remove if you want unlimited accounts per user)
        if user:
            user_accounts_count = TelegramAccount.objects.filter(user=user).count()
            if self.instance and self.instance.pk and self.instance.user == user:
                user_accounts_count -= 1  # Don't count the current account being edited
            
            # Set a reasonable limit - adjust as needed
            MAX_ACCOUNTS_PER_USER = 10
            if user_accounts_count >= MAX_ACCOUNTS_PER_USER:
                raise ValidationError(f"User {user.email} already has {user_accounts_count} accounts assigned. Maximum allowed is {MAX_ACCOUNTS_PER_USER}.")
        
        return cleaned_data

class BulkSyncForm(Form):
    """Form for triggering bulk sync of session files"""
    sync_all = widgets.CheckboxInput()

@admin.register(TelegramAccount)
class TelegramAccountAdmin(admin.ModelAdmin):
    form = TelegramAccountAdminForm
    list_display = ['id', 'phone', 'username', 'first_name', 'last_name', 'user_info', 'is_active', 'session_file_status']
    list_filter = ['is_active', 'user', 'last_seen']
    search_fields = ['phone', 'username', 'first_name', 'last_name', 'user__email', 'user__name']
    raw_id_fields = ['user']
    actions = ['sync_selected_accounts', 'assign_to_user', 'unassign_from_user', 'bulk_assign_users']
    
    fieldsets = (
        ('Account Info', {
            'fields': ('user', 'phone', 'username', 'first_name', 'last_name', 'gender')
        }),
        ('Session Management', {
            'fields': ('session_file', 'session_file_upload', 'is_active')
        }),
        ('Statistics', {
            'fields': ('unread_count', 'last_seen'),
            'classes': ('collapse',)
        }),
        ('Photo', {
            'fields': ('photo',),
            'classes': ('collapse',)
        })
    )
    
    def user_info(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.user.name or obj.user.email,
                obj.user.email
            )
        return format_html('<span style="color: orange;">⚠️ Unassigned</span>')
    user_info.short_description = 'Assigned User'

    def session_file_status(self, obj):
        if obj.session_file:
            session_path = os.path.join('sessions', obj.session_file)
            if os.path.exists(session_path):
                return format_html('<span style="color: green;">✓ Active</span>')
            else:
                return format_html('<span style="color: red;">✗ Missing</span>')
        return format_html('<span style="color: orange;">No session file</span>')
    session_file_status.short_description = 'Session Status'
    
    def save_model(self, request, obj, form, change):
        # Handle session file upload
        if 'session_file_upload' in form.cleaned_data and form.cleaned_data['session_file_upload']:
            uploaded_file = form.cleaned_data['session_file_upload']
            
            # Create sessions directory if it doesn't exist
            sessions_dir = os.path.join('sessions')
            os.makedirs(sessions_dir, exist_ok=True)
            
            # Generate filename
            filename = f"session_{obj.phone or obj.username or obj.id}.session"
            file_path = os.path.join(sessions_dir, filename)
            
            # Save the uploaded file
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Update the session_file field
            obj.session_file = filename
        
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        """Add custom URLs for bulk upload and sync actions"""
        urls = super().get_urls()
        custom_urls = [
            path('session-management/', self.admin_site.admin_view(self.upload_multiple_sessions), name='session-management'),
            path('sync-all/', self.admin_site.admin_view(self.sync_all_sessions), name='sync-all-sessions'),
            path('assign-accounts-to-user/', self.admin_site.admin_view(self.assign_accounts_to_user_view), name='assign-accounts-to-user'),
            path('bulk-assign-users/', self.admin_site.admin_view(self.bulk_assign_users_view), name='bulk-assign-users'),
            path('user-assignment-management/', self.admin_site.admin_view(self.user_assignment_management), name='user-assignment-management'),
            path('assign-single/', self.admin_site.admin_view(self.assign_single_account_api), name='assign-single-account'),
            path('bulk-assign-api/', self.admin_site.admin_view(self.bulk_assign_api), name='bulk-assign-api'),
        ]
        return custom_urls + urls
    
    def upload_multiple_sessions(self, request):
        """Handle session files management page with upload functionality"""
        sessions_dir = 'sessions'
        
        # Handle file upload POST request
        if request.method == 'POST' and request.FILES:
            uploaded_count = 0
            errors = []
            
            # Create sessions directory if it doesn't exist
            os.makedirs(sessions_dir, exist_ok=True)
            
            # Handle multiple file uploads
            uploaded_files = request.FILES.getlist('session_files')
            
            for uploaded_file in uploaded_files:
                # Validate file extension
                if not uploaded_file.name.endswith('.session'):
                    errors.append(f"Invalid file type for {uploaded_file.name}. Only .session files are allowed.")
                    continue
                
                file_path = os.path.join(sessions_dir, uploaded_file.name)
                
                # Check if file already exists
                if os.path.exists(file_path):
                    errors.append(f"File {uploaded_file.name} already exists. Use a different name or delete the existing file first.")
                    continue
                
                try:
                    # Save the file
                    with open(file_path, 'wb+') as destination:
                        for chunk in uploaded_file.chunks():
                            destination.write(chunk)
                    uploaded_count += 1
                except Exception as e:
                    errors.append(f"Failed to save {uploaded_file.name}: {str(e)}")
            
            # Show results
            if uploaded_count > 0:
                messages.success(request, f"Successfully uploaded {uploaded_count} session files.")
            
            if errors:
                for error in errors:
                    messages.error(request, error)
            
            # Redirect to avoid re-upload on refresh
            return redirect(request.path)
        
        # Get existing session files
        session_files = []
        if os.path.exists(sessions_dir):
            session_files = [f for f in os.listdir(sessions_dir) if f.endswith('.session')]
        
        # Get existing accounts and their session files
        existing_accounts = TelegramAccount.objects.all()
        accounts_with_sessions = {acc.session_file: acc for acc in existing_accounts if acc.session_file}
        
        # Create session file data with account info
        session_file_data = []
        for filename in session_files:
            account = accounts_with_sessions.get(filename)
            session_file_data.append({
                'filename': filename,
                'has_account': account is not None,
                'account': account
            })
        
        context = {
            'title': 'Session Files Management',
            'session_file_data': session_file_data,
            'sessions_dir': sessions_dir,
            'has_change_permission': True,
            'site_header': self.admin_site.site_header,
            'site_title': self.admin_site.site_title,
        }
        return render(request, 'admin/session_management.html', context)
    
    def sync_all_sessions(self, request):
        """Sync all session files using telegram_sync/sync_chats.py"""
        try:
            # Get all session files from the sessions directory
            sessions_dir = 'sessions'
            if not os.path.exists(sessions_dir):
                messages.error(request, "Sessions directory does not exist.")
                return redirect('..')
            
            session_files = [f for f in os.listdir(sessions_dir) if f.endswith('.session')]
            
            if not session_files:
                messages.warning(request, "No session files found to sync.")
                return redirect('..')
            
            # Call the sync_chats.py script
            sync_script_path = os.path.join('telegram_sync', 'sync_chats.py')
            
            if not os.path.exists(sync_script_path):
                messages.error(request, "sync_chats.py script not found.")
                return redirect('..')
            
            # Run the sync script asynchronously
            try:
                # Import and run the sync function
                import sys
                import os
                
                # Add the project root to the Python path
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                
                # Import the sync_chats module
                from telegram_sync import sync_chats
                
                # Run the sync in a separate process to avoid blocking the admin interface
                import threading
                
                def run_sync():
                    try:
                        asyncio.run(sync_chats.main())
                    except Exception as e:
                        print(f"Sync error: {e}")
                
                sync_thread = threading.Thread(target=run_sync)
                sync_thread.daemon = True
                sync_thread.start()
                
                messages.success(request, f"Sync started for {len(session_files)} session files. Check the logs for progress.")
                
            except ImportError as e:
                messages.error(request, f"Failed to import sync_chats module: {str(e)}")
            except Exception as e:
                messages.error(request, f"Failed to start sync: {str(e)}")
                
        except Exception as e:
            messages.error(request, f"Error during sync: {str(e)}")
        
        return redirect('..')
    
    def sync_selected_accounts(self, request, queryset):
        """Admin action to sync selected accounts"""
        session_files = []
        for account in queryset:
            if account.session_file:
                session_files.append(account.session_file)
        
        if not session_files:
            messages.warning(request, "No session files found for selected accounts.")
            return
        
        try:
            # Import and run the sync function for specific session files
            import sys
            import os
            
            # Add the project root to the Python path
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from telegram_sync import sync_chats
            
            # Run the sync in a separate thread
            import threading
            
            def run_sync():
                try:
                    # Convert relative session files to full paths
                    full_session_paths = [os.path.join('sessions', sf) for sf in session_files]
                    asyncio.run(sync_chats.main(session_files=full_session_paths))
                except Exception as e:
                    print(f"Sync error: {e}")
            
            sync_thread = threading.Thread(target=run_sync)
            sync_thread.daemon = True
            sync_thread.start()
            
            messages.success(request, f"Sync started for {len(session_files)} selected accounts.")
            
        except Exception as e:
            messages.error(request, f"Failed to start sync: {str(e)}")
    
    sync_selected_accounts.short_description = "Sync selected accounts with Telegram"

    def assign_to_user(self, request, queryset):
        """Admin action to assign selected accounts to a user"""
        unassigned_count = queryset.filter(user__isnull=True).count()
        
        if unassigned_count == 0:
            messages.warning(request, "All selected accounts are already assigned to users.")
            return
        
        # For now, redirect to a custom page for user selection
        # Store the account IDs in session for the assignment page
        account_ids = list(queryset.values_list('id', flat=True))
        request.session['accounts_to_assign'] = account_ids
        
        return HttpResponseRedirect(reverse('admin:assign-accounts-to-user'))
    
    assign_to_user.short_description = "Assign selected accounts to a user"

    def unassign_from_user(self, request, queryset):
        """Admin action to unassign selected accounts from users"""
        assigned_count = queryset.filter(user__isnull=False).count()
        
        if assigned_count == 0:
            messages.warning(request, "No selected accounts are assigned to users.")
            return
        
        # Unassign users from selected accounts
        updated = queryset.update(user=None)
        messages.success(request, f"Successfully unassigned {updated} accounts from their users.")
    
    unassign_from_user.short_description = "Unassign selected accounts from users"

    def bulk_assign_users(self, request, queryset):
        """Admin action for bulk user assignment"""
        return HttpResponseRedirect(reverse('admin:bulk-assign-users') + f"?ids={','.join(map(str, queryset.values_list('id', flat=True)))}")
    
    bulk_assign_users.short_description = "Bulk assign users to accounts"

    def assign_accounts_to_user_view(self, request):
        """View for assigning accounts to a specific user"""
        if request.method == 'POST':
            user_id = request.POST.get('user_id')
            account_ids = request.session.get('accounts_to_assign', [])
            
            if user_id and account_ids:
                try:
                    user = User.objects.get(id=user_id)
                    accounts = TelegramAccount.objects.filter(id__in=account_ids, user__isnull=True)
                    updated = accounts.update(user=user)
                    
                    messages.success(request, f"Successfully assigned {updated} accounts to {user.name or user.email}")
                    
                    # Clear session data
                    if 'accounts_to_assign' in request.session:
                        del request.session['accounts_to_assign']
                        
                except User.DoesNotExist:
                    messages.error(request, "Selected user does not exist.")
                except Exception as e:
                    messages.error(request, f"Error assigning accounts: {str(e)}")
            
            return redirect('admin:api_telegramaccount_changelist')
        
        # GET request - show assignment form
        account_ids = request.session.get('accounts_to_assign', [])
        if not account_ids:
            messages.error(request, "No accounts selected for assignment.")
            return redirect('admin:api_telegramaccount_changelist')
        
        accounts = TelegramAccount.objects.filter(id__in=account_ids)
        users = User.objects.filter(is_active=True).order_by('name', 'email')
        
        context = {
            'title': 'Assign Accounts to User',
            'accounts': accounts,
            'users': users,
            'has_change_permission': True,
            'site_header': self.admin_site.site_header,
            'site_title': self.admin_site.site_title,
        }
        return render(request, 'admin/assign_accounts_to_user.html', context)

    def bulk_assign_users_view(self, request):
        """View for bulk user assignment with individual selection"""
        account_ids = request.GET.get('ids', '').split(',') if request.GET.get('ids') else []
        
        if request.method == 'POST':
            assignments = []
            for key, value in request.POST.items():
                if key.startswith('user_') and value:
                    account_id = key.replace('user_', '')
                    try:
                        account_id = int(account_id)
                        user_id = int(value) if value != 'unassign' else None
                        assignments.append((account_id, user_id))
                    except (ValueError, TypeError):
                        continue
            
            if assignments:
                try:
                    updated_count = 0
                    for account_id, user_id in assignments:
                        account = TelegramAccount.objects.get(id=account_id)
                        if user_id:
                            user = User.objects.get(id=user_id)
                            account.user = user
                        else:
                            account.user = None
                        account.save()
                        updated_count += 1
                    
                    messages.success(request, f"Successfully updated assignments for {updated_count} accounts.")
                    
                except Exception as e:
                    messages.error(request, f"Error updating assignments: {str(e)}")
            
            return redirect('admin:api_telegramaccount_changelist')
        
        # GET request - show bulk assignment form
        if not account_ids or not account_ids[0]:
            messages.error(request, "No accounts selected for bulk assignment.")
            return redirect('admin:api_telegramaccount_changelist')
        
        try:
            account_ids = [int(id) for id in account_ids if id]
            accounts = TelegramAccount.objects.filter(id__in=account_ids)
            users = User.objects.filter(is_active=True).order_by('name', 'email')
            
            context = {
                'title': 'Bulk Assign Users to Accounts',
                'accounts': accounts,
                'users': users,
                'has_change_permission': True,
                'site_header': self.admin_site.site_header,
                'site_title': self.admin_site.site_title,
            }
            return render(request, 'admin/bulk_assign_users.html', context)
            
        except (ValueError, TypeError):
            messages.error(request, "Invalid account IDs provided.")
            return redirect('admin:api_telegramaccount_changelist')

    def user_assignment_management(self, request):
        """Comprehensive user assignment management view"""
        # Get all users and their assigned accounts
        users = User.objects.filter(is_active=True).prefetch_related('telegramaccount_set')
        unassigned_accounts = TelegramAccount.objects.filter(user__isnull=True)
        
        context = {
            'title': 'User Assignment Management',
            'users': users,
            'unassigned_accounts': unassigned_accounts,
            'has_change_permission': True,
            'site_header': self.admin_site.site_header,
            'site_title': self.admin_site.site_title,
        }
        return render(request, 'admin/user_assignment_management.html', context)

    def assign_single_account_api(self, request):
        """API endpoint for single account assignment"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'POST method required'})
        
        try:
            import json
            data = json.loads(request.body)
            account_id = data.get('account_id')
            user_id = data.get('user_id')
            
            account = TelegramAccount.objects.get(id=account_id)
            
            if user_id:
                user = User.objects.get(id=user_id)
                
                # Check if user is active
                if not user.is_active:
                    return JsonResponse({'success': False, 'error': 'Cannot assign account to inactive user'})
                
                # Check account limits (optional)
                MAX_ACCOUNTS_PER_USER = 10
                user_accounts_count = TelegramAccount.objects.filter(user=user).exclude(id=account_id).count()
                if user_accounts_count >= MAX_ACCOUNTS_PER_USER:
                    return JsonResponse({
                        'success': False, 
                        'error': f'User already has {user_accounts_count} accounts. Maximum allowed is {MAX_ACCOUNTS_PER_USER}.'
                    })
                
                account.user = user
            else:
                account.user = None
            
            account.save()
            
            return JsonResponse({'success': True})
            
        except (TelegramAccount.DoesNotExist, User.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'Account or user not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    def bulk_assign_api(self, request):
        """API endpoint for bulk account assignment"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'POST method required'})
        
        try:
            import json
            data = json.loads(request.body)
            account_ids = data.get('account_ids', [])
            user_id = data.get('user_id')
            
            if not account_ids:
                return JsonResponse({'success': False, 'error': 'No accounts selected'})
            
            if user_id:
                user = User.objects.get(id=user_id)
                
                # Check if user is active
                if not user.is_active:
                    return JsonResponse({'success': False, 'error': 'Cannot assign accounts to inactive user'})
                
                # Check account limits for bulk assignment
                MAX_ACCOUNTS_PER_USER = 10
                current_user_accounts = TelegramAccount.objects.filter(user=user).exclude(id__in=account_ids).count()
                new_assignments = len(account_ids)
                total_after_assignment = current_user_accounts + new_assignments
                
                if total_after_assignment > MAX_ACCOUNTS_PER_USER:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Bulk assignment would give user {total_after_assignment} accounts. Maximum allowed is {MAX_ACCOUNTS_PER_USER}. User currently has {current_user_accounts} accounts.'
                    })
                
                user = user
            else:
                user = None
            
            accounts = TelegramAccount.objects.filter(id__in=account_ids)
            updated = accounts.update(user=user)
            
            return JsonResponse({
                'success': True, 
                'updated_count': updated
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

@admin.register(TelegramChat)
class TelegramChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'telegram_account_id', 'unread_count', 'last_message_time']
    list_filter = ['type', 'telegram_account_id', 'is_active']
    search_fields = ['name', 'username']
    
    def get_telegram_account(self, obj):
        try:
            from .models import TelegramAccount
            account = TelegramAccount.objects.get(id=obj.telegram_account_id)
            return f"{account.username or account.phone}"
        except:
            return f"Account ID: {obj.telegram_account_id}"
    get_telegram_account.short_description = 'Telegram Account'

@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'chat_id', 'telegram_account_id', 'sender_id', 'message_preview', 'date', 'is_read']
    list_filter = ['is_read', 'date', 'telegram_account_id']
    search_fields = ['text']
    
    def message_preview(self, obj):
        if obj.text:
            return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
        return "No text content"
    message_preview.short_description = 'Message Preview'
