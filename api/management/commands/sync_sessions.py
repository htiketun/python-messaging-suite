from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from api.models import TelegramAccount
import os
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Sync session files with Telegram accounts in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-accounts',
            action='store_true',
            help='Create new TelegramAccount entries for session files without accounts',
        )
        parser.add_argument(
            '--assign-user',
            type=int,
            help='User ID to assign to newly created accounts',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        sessions_dir = 'sessions'
        
        if not os.path.exists(sessions_dir):
            self.stdout.write(
                self.style.WARNING(f'Sessions directory "{sessions_dir}" does not exist')
            )
            return

        # Get all session files
        session_files = [f for f in os.listdir(sessions_dir) if f.endswith('.session')]
        
        if not session_files:
            self.stdout.write(
                self.style.WARNING('No session files found in sessions directory')
            )
            return

        self.stdout.write(f'Found {len(session_files)} session files')
        
        # Get existing accounts
        existing_accounts = TelegramAccount.objects.all()
        existing_session_files = set(acc.session_file for acc in existing_accounts if acc.session_file)
        
        self.stdout.write(f'Found {len(existing_accounts)} existing Telegram accounts')
        self.stdout.write(f'Found {len(existing_session_files)} accounts with session files')

        # Find orphaned session files (files without accounts)
        orphaned_files = set(session_files) - existing_session_files
        
        # Find missing session files (accounts with files that don't exist)
        missing_files = []
        for account in existing_accounts:
            if account.session_file and account.session_file not in session_files:
                missing_files.append(account)

        # Report findings
        self.stdout.write('\n' + '='*50)
        self.stdout.write('SYNC STATUS REPORT')
        self.stdout.write('='*50)
        
        self.stdout.write(f'Session files in directory: {len(session_files)}')
        self.stdout.write(f'Accounts with session files: {len(existing_session_files)}')
        self.stdout.write(f'Orphaned session files: {len(orphaned_files)}')
        self.stdout.write(f'Accounts with missing files: {len(missing_files)}')

        if orphaned_files:
            self.stdout.write('\nORPHANED SESSION FILES:')
            for filename in orphaned_files:
                self.stdout.write(f'  - {filename}')

        if missing_files:
            self.stdout.write('\nACCOUNTS WITH MISSING SESSION FILES:')
            for account in missing_files:
                self.stdout.write(f'  - Account ID {account.id}: {account.session_file} (User: {account.user.email if account.user else "None"})')

        # Handle creating accounts for orphaned files
        if options['create_accounts'] and orphaned_files:
            self.stdout.write('\n' + '-'*30)
            self.stdout.write('CREATING ACCOUNTS FOR ORPHANED FILES')
            self.stdout.write('-'*30)
            
            user = None
            if options['assign_user']:
                try:
                    user = User.objects.get(id=options['assign_user'])
                    self.stdout.write(f'Will assign new accounts to user: {user.email}')
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'User with ID {options["assign_user"]} does not exist')
                    )
                    return

            created_count = 0
            for filename in orphaned_files:
                if options['dry_run']:
                    self.stdout.write(f'[DRY RUN] Would create account for: {filename}')
                else:
                    try:
                        # Extract phone or username from filename if possible
                        phone = None
                        username = None
                        
                        # Try to extract phone number from filename
                        if '+' in filename:
                            phone_part = filename.split('+')[1].split('.')[0]
                            if phone_part.isdigit():
                                phone = '+' + phone_part
                        
                        # Try to extract username (assuming format like "session_username.session")
                        if not phone and 'session_' in filename:
                            potential_username = filename.replace('session_', '').replace('.session', '')
                            if potential_username and not potential_username.startswith('+'):
                                username = potential_username

                        account = TelegramAccount.objects.create(
                            session_file=filename,
                            phone=phone,
                            username=username,
                            user=user,
                            is_active=True
                        )
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'Created account ID {account.id} for {filename}')
                        )
                        created_count += 1
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Failed to create account for {filename}: {str(e)}')
                        )

            if not options['dry_run']:
                self.stdout.write(f'\nCreated {created_count} new accounts')

        # Handle missing files
        if missing_files:
            self.stdout.write('\n' + '-'*30)
            self.stdout.write('ACCOUNTS WITH MISSING SESSION FILES')
            self.stdout.write('-'*30)
            
            for account in missing_files:
                if options['dry_run']:
                    self.stdout.write(f'[DRY RUN] Account ID {account.id} missing file: {account.session_file}')
                else:
                    self.stdout.write(f'Account ID {account.id} missing file: {account.session_file}')
                    # You might want to mark these accounts as inactive or handle them differently

        self.stdout.write('\n' + '='*50)
        self.stdout.write('SYNC COMPLETE')
        self.stdout.write('='*50)

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('This was a dry run. No changes were made.'))
        else:
            self.stdout.write(self.style.SUCCESS('Sync completed successfully!'))

    def _get_session_info(self, filepath):
        """
        Try to extract information from session file (if readable)
        This is optional and depends on the session file format
        """
        try:
            # This is a placeholder - actual implementation would depend
            # on the Telegram session file format
            return {}
        except:
            return {}