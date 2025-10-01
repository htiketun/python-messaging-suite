from django.core.management.base import BaseCommand
from telegram_sync.telethon_service import telethon_service
import asyncio


class Command(BaseCommand):
    help = 'Test Telegram authentication setup'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Telegram authentication setup...'))
        
        # Test service initialization
        try:
            account_id = telethon_service.generate_account_id()
            self.stdout.write(f'Generated account ID: {account_id}')
            
            # Test client creation (without connecting)
            client = telethon_service.get_client(account_id)
            self.stdout.write(f'Created client: {client}')
            
            self.stdout.write(self.style.SUCCESS('✓ Telegram service setup is working'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error in Telegram service setup: {e}')
            )
            
        self.stdout.write(self.style.SUCCESS('Test completed!'))