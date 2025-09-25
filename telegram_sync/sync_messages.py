import asyncio
import os
from telethon import TelegramClient, errors
import telegram_sync.config as config
import telegram_sync.session_manager as sm
import telegram_sync.db as db

async def sync_dialog_messages(client, conn, telegram_account_id, dialog_id, direction="latest", limit=10):
    """
    Sync messages for a dialog.
    direction: "latest" (default) for latest N messages,
               "new" for messages after last synced,
               "old" for messages before oldest synced
    """
    try:
        if direction == "latest":
            messages = [msg async for msg in client.iter_messages(dialog_id, limit=limit)]
            for msg in reversed(messages):  # Oldest first
                await db.upsert_message(conn, telegram_account_id, dialog_id, msg)
            if messages:
                await db.set_last_synced_message(conn, telegram_account_id, dialog_id, messages[0].id, messages[0].date)  # oldest
                await db.set_last_synced_message(conn, telegram_account_id, dialog_id, messages[-1].id, messages[-1].date)  # newest

        elif direction == "new":
            last_synced_id = await db.get_last_synced_message(conn, telegram_account_id, dialog_id, newest=True)
            async for msg in client.iter_messages(dialog_id, min_id=(last_synced_id or 0)):
                await db.upsert_message(conn, telegram_account_id, dialog_id, msg)
                if not last_synced_id or msg.id > last_synced_id:
                    last_synced_id = msg.id
                    await db.set_last_synced_message(conn, telegram_account_id, dialog_id, last_synced_id, msg.date, newest=True)

        elif direction == "old":
            oldest_synced_id = await db.get_last_synced_message(conn, telegram_account_id, dialog_id, newest=False)
            async for msg in client.iter_messages(dialog_id, max_id=(oldest_synced_id or 0), reverse=True, limit=limit):
                await db.upsert_message(conn, telegram_account_id, dialog_id, msg)
                if not oldest_synced_id or msg.id < oldest_synced_id:
                    oldest_synced_id = msg.id
                    await db.set_last_synced_message(conn, telegram_account_id, dialog_id, oldest_synced_id, msg.date, newest=False)
    except errors.FloodWaitError as e:
        print(f"FloodWait: Sleeping for {e.seconds} seconds...")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"Error syncing dialog {dialog_id}: {e}")

async def fetch_and_sync_messages(session_file, conn, chat_id=None, direction="latest", limit=10):
    telegram_account_id = await db.get_telegram_account_id(conn, session_file)
    async with TelegramClient(session_file, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH) as client:
        if chat_id:
            dialog = await client.get_entity(chat_id)
            await sync_dialog_messages(client, conn, telegram_account_id, dialog.id, direction=direction, limit=limit)
        else:
            chat_ids = await db.get_chat_ids_from_telegram_chat(conn, telegram_account_id)
            if chat_ids:
                for cid in chat_ids:
                    await sync_dialog_messages(client, conn, telegram_account_id, cid, direction=direction, limit=limit)
            else:
                print(f"No chats found for account {telegram_account_id}. Please run sync_chats.py first.")

async def main(full_sync=False, session_files=None, chat_id=None, direction="latest", limit=10):
    if session_files is None:
        session_files = sm.get_session_files()
    if not session_files:
        print("No session files found. Exiting.")
        return

    conn = await db.get_db()
    for sess in session_files:
        try:
            await fetch_and_sync_messages(sess, conn, chat_id=chat_id, direction=direction, limit=limit)
        except errors.FloodWaitError as e:
            print(f"FloodWait: Sleeping for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Error with session {sess}: {e}")
    await conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_file", type=str, help="Path to the session file")
    parser.add_argument("--chat_id", type=int, help="Chat ID to sync")
    parser.add_argument("--full", action="store_true", help="Perform a full sync (all messages)")
    parser.add_argument("--direction", type=str, choices=["latest", "new", "old"], default="latest", help="Direction to sync messages")
    parser.add_argument("--limit", type=int, default=100, help="Limit the number of messages to sync")
    args = parser.parse_args()
    session_files = [args.session_file] if args.session_file else None
    session_files = sm.get_session_files(session_files)
    asyncio.run(main(full_sync=args.full, session_files=session_files, chat_id=args.chat_id, direction=args.direction, limit=args.limit))
