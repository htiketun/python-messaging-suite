import asyncio
import os
from telethon import TelegramClient, errors
import telegram_sync.config as config
import telegram_sync.session_manager as sm
import telegram_sync.db as db

async def sync_dialog_messages(client, conn, sync_session, dialog_id, direction="latest", limit=10):
    """
    direction: "latest" (default) for latest N messages, "new" for messages after last synced, "old" for messages before oldest synced
    """
    if direction == "latest":
        # Fetch latest N messages
        messages = [msg async for msg in client.iter_messages(dialog_id, limit=limit)]
        print(f"Initial load for dialog {dialog_id}, fetched {len(messages)} messages")
        for msg in reversed(messages):  # Oldest first
            await db.upsert_message(conn, sync_session, dialog_id, msg)
        if messages:
            await db.set_last_synced_message(conn, sync_session, dialog_id, messages[0].id, messages[0].date)  # oldest
            await db.set_last_synced_message(conn, sync_session, dialog_id, messages[-1].id, messages[-1].date)  # newest
        await asyncio.sleep(1)
    elif direction == "new":
        # Fetch messages after last synced (newer messages)
        last_synced_id = await db.get_last_synced_message(conn, sync_session, dialog_id, newest=True)
        total_msgs = 0
        last_message_time = None
        async for msg in client.iter_messages(dialog_id, min_id=(last_synced_id or 0)):
            await db.upsert_message(conn, sync_session, dialog_id, msg)
            print(f"New message for dialog {dialog_id}, ID {msg.id}")
            if not last_synced_id or msg.id > last_synced_id:
                last_synced_id = msg.id
                last_message_time = msg.date
            total_msgs += 1
            if total_msgs % 100 == 0:
                await asyncio.sleep(1)
        if last_synced_id and last_message_time:
            await db.set_last_synced_message(conn, sync_session, dialog_id, last_synced_id, last_message_time, newest=True)
        await asyncio.sleep(1)
    elif direction == "old":
        # Fetch messages before oldest synced (older messages)
        oldest_synced_id = await db.get_last_synced_message(conn, sync_session, dialog_id, newest=False)
        total_msgs = 0
        oldest_message_time = None
        async for msg in client.iter_messages(dialog_id, max_id=(oldest_synced_id or 0), reverse=True, limit=limit):
            await db.upsert_message(conn, sync_session, dialog_id, msg)
            print(f"Old message for dialog {dialog_id}, ID {msg.id}")
            if not oldest_synced_id or msg.id < oldest_synced_id:
                oldest_synced_id = msg.id
                oldest_message_time = msg.date
            total_msgs += 1
            if total_msgs % 100 == 0:
                await asyncio.sleep(1)
        if oldest_synced_id and oldest_message_time:
            await db.set_last_synced_message(conn, sync_session, dialog_id, oldest_synced_id, oldest_message_time, newest=False)
        await asyncio.sleep(1)

async def fetch_and_sync_messages(session_file, conn, full_sync=False, chat_id=None, direction="latest", limit=10):
    async with TelegramClient(session_file, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH) as client:
        sync_session = os.path.basename(session_file)
        if chat_id:
            dialog = await client.get_entity(chat_id)
            await sync_dialog_messages(client, conn, sync_session, dialog.id, direction=direction, limit=limit)
        else:
            async for dialog in client.iter_dialogs():
                await sync_dialog_messages(client, conn, sync_session, dialog.id, direction=direction, limit=limit)

async def main(full_sync=False, session_files=None, chat_id=None, direction="latest", limit=10):
    if session_files is None:
        session_files = sm.get_session_files()
    if not session_files:
        print("No session files found. Exiting.")
        return

    conn = await db.get_db()
    for sess in session_files:
        try:
            await fetch_and_sync_messages(sess, conn, full_sync=full_sync, chat_id=chat_id, direction=direction, limit=limit)
        except errors.FloodWaitError as e:
            print(f"FloodWait: Sleeping for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(e)
            exit()
            print(f"Error with session {sess}: {e}")
    await conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_file", type=str, help="Path to the session file")
    # Example chat_id: 2119338760 or -1002119338760
    parser.add_argument("--chat_id", type=int, help="Chat ID to sync")
    parser.add_argument("--full", action="store_true", help="Perform a full sync (all messages)")
    parser.add_argument("--direction", type=str, choices=["new", "old"], default="new", help="Direction to sync messages")
    parser.add_argument("--limit", type=int, default=100, help="Limit the number of messages to sync")
    args = parser.parse_args()
    session_files = [args.session_file] if args.session_file else None
    session_files = sm.get_session_files(session_files)
    asyncio.run(main(full_sync=args.full, session_files=session_files, chat_id=args.chat_id, direction=args.direction, limit=args.limit))
