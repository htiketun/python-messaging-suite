import argparse
import asyncio
import uuid
import os
import telegram_sync.session_manager as sm
import telegram_sync.config as config
import telegram_sync.db as db  # Add this import for db
from telethon import errors
os.makedirs(config.SESSION_FOLDER, exist_ok=True)

async def main(sync_all=False):
    if sync_all:
        print("Creating a Telegram session from session folder...")
        session_files = [
            os.path.join(config.SESSION_FOLDER, f)
            for f in os.listdir(config.SESSION_FOLDER)
            if f.endswith('.session')
        ]

        for session_file in session_files:
            print(f"Syncing all chats and messages for session file: {session_file}")
            username = os.path.splitext(os.path.basename(session_file))[0]
            client = sm.new_session(username)
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    await client.disconnect()
                    os.remove(session_file)
                    print(f"Skipping {username}: session is not authorized or requires login.")
                    continue
                conn = await db.get_db()
                me = await client.get_me()
                await db.upsert_telegram_account(conn, os.path.basename(client.session.filename), me)
                print(f"Finished syncing for session file: {session_file}")
            except Exception as e:
                print(f"Skipping {username}: encountered an error: {e}")
                continue
        return
    else:
        print("Creating a new Telegram session...")
        username = f"session_{uuid.uuid4().hex[:8]}"
        print(f"Generated unique session username: {username}")
        client = sm.new_session(username)
        await client.start()
        conn = await db.get_db()
        me = await client.get_me()
        await db.upsert_telegram_account(conn, os.path.basename(client.session.filename), me)
        print(f"Session for {username} created.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync-all", action="store_true", help="Sync all chats and messages for all session files after creating session")
    args = parser.parse_args()
    asyncio.run(main(sync_all=args.sync_all))