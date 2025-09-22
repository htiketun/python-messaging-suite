from telethon import TelegramClient
import asyncio
import uuid
import os
import telegram_sync.session_manager as sm
import telegram_sync.config as config
os.makedirs(config.SESSION_FOLDER, exist_ok=True)

async def main():
    username = f"session_{uuid.uuid4().hex[:8]}"
    print(f"Generated unique session username: {username}")
    client = sm.new_session(username)
    await client.start()
    print(f"Session for {username} created.")

if __name__ == "__main__":
    asyncio.run(main())