import os
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'python-messaging-suite.settings')

from telegram_sync.telethon_service import telethon_service

async def autologin_all_sessions():
    session_folder = telethon_service.session_folder
    session_files = [f for f in os.listdir(session_folder) if f.endswith('.session')]
    for session_file in session_files:
        account_id = os.path.splitext(session_file)[0]
        try:
            await telethon_service.start_client(account_id)
            print(f"Autologin successful for account: {account_id}")
        except Exception as e:
            print(f"Autologin failed for account: {account_id} - {e}")

if __name__ == "__main__":
    asyncio.run(autologin_all_sessions())
