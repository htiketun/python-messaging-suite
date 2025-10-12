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
               "new" for messages after last synced (newer than newest),
               "old" for messages before oldest synced (older than oldest)
    """
    if dialog_id == 777000:
        dialog_id = telegram_account_id  # Handle Telegram system messages
    try:
        if direction == "latest":
            # iter_messages returns newest to oldest by default
            messages = [msg async for msg in client.iter_messages(dialog_id, limit=limit)]
            
            if messages:
                # Insert messages (can be in any order for upsert)
                for msg in messages:
                    await db.upsert_message(conn, telegram_account_id, dialog_id, msg)
                
                # messages[0] is newest, messages[-1] is oldest
                newest_msg = messages[0]  # First = newest
                oldest_msg = messages[-1]  # Last = oldest
                
                # Set sync boundaries
                await db.set_last_synced_message(conn, telegram_account_id, dialog_id, newest_msg.id, newest_msg.date, newest=True)
                await db.set_last_synced_message(conn, telegram_account_id, dialog_id, oldest_msg.id, oldest_msg.date, newest=False)
                
                print(f"Synced {len(messages)} latest messages for dialog {dialog_id} (newest: {newest_msg.id}, oldest: {oldest_msg.id})")

        elif direction == "new":
            # Get the newest synced message ID
            newest_synced_id = await db.get_last_synced_message(conn, telegram_account_id, dialog_id, newest=True)
            
            if newest_synced_id is None:
                print(f"No previous sync found for dialog {dialog_id}. Use 'latest' direction first.")
                return
            
            new_messages = []
            # Get messages newer than the newest we've synced
            async for msg in client.iter_messages(dialog_id, min_id=newest_synced_id):
                new_messages.append(msg)
                await db.upsert_message(conn, telegram_account_id, dialog_id, msg)
            
            if new_messages:
                # Update the newest synced message (messages are newest first)
                newest_new = new_messages[0]
                await db.set_last_synced_message(conn, telegram_account_id, dialog_id, newest_new.id, newest_new.date, newest=True)
                print(f"Synced {len(new_messages)} new messages for dialog {dialog_id} (newest: {newest_new.id})")
            else:
                print(f"No new messages found for dialog {dialog_id}")

        elif direction == "old":
            # Get the oldest synced message ID
            oldest_synced_id = await db.get_last_synced_message(conn, telegram_account_id, dialog_id, newest=False)
            
            if oldest_synced_id is None:
                print(f"No previous sync found for dialog {dialog_id}. Use 'latest' direction first.")
                return
            
            old_messages = []
            # Get messages older than the oldest we've synced (max_id excludes the message with that ID)
            async for msg in client.iter_messages(dialog_id, max_id=oldest_synced_id, limit=limit):
                old_messages.append(msg)
                await db.upsert_message(conn, telegram_account_id, dialog_id, msg)
            
            if old_messages:
                # Update the oldest synced message (messages are newest first, so last is oldest)
                oldest_new = old_messages[-1]
                await db.set_last_synced_message(conn, telegram_account_id, dialog_id, oldest_new.id, oldest_new.date, newest=False)
                print(f"Synced {len(old_messages)} old messages for dialog {dialog_id} (oldest: {oldest_new.id})")
            else:
                print(f"No older messages found for dialog {dialog_id}")
    except errors.FloodWaitError as e:
        print(f"FloodWait for dialog {dialog_id}: Sleeping for {e.seconds} seconds...")
        await asyncio.sleep(e.seconds)
        # Retry the operation after flood wait
        print(f"Retrying sync for dialog {dialog_id} after flood wait...")
        await sync_dialog_messages(client, conn, telegram_account_id, dialog_id, direction, limit)
    except errors.ChatAdminRequiredError:
        print(f"Admin permissions required for dialog {dialog_id}. Skipping.")
    except errors.ChannelPrivateError:
        print(f"Dialog {dialog_id} is private or not accessible. Skipping.")
    except errors.PeerIdInvalidError:
        print(f"Invalid peer ID {dialog_id}. Skipping.")
    except Exception as e:
        print(f"Unexpected error syncing dialog {dialog_id}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def fetch_and_sync_messages(session_file, conn, chat_id=None, direction="latest", limit=10):
    try:
        telegram_account_id = await db.get_telegram_account_id(conn, session_file)
        if not telegram_account_id:
            print(f"No telegram account found for session {session_file}")
            return
            
        print(f"Starting message sync for account {telegram_account_id} (session: {os.path.basename(session_file)})")
        
        async with TelegramClient(session_file, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH) as client:
            if chat_id:
                try:
                    dialog = await client.get_entity(chat_id)
                    print(f"Syncing specific chat: {chat_id} (direction: {direction}, limit: {limit})")
                    await sync_dialog_messages(client, conn, telegram_account_id, dialog.id, direction=direction, limit=limit)
                except Exception as e:
                    print(f"Error getting entity for chat_id {chat_id}: {e}")
            else:
                chat_ids = await db.get_chat_ids_from_telegram_chat(conn, telegram_account_id)
                if chat_ids:
                    print(f"Found {len(chat_ids)} chats to sync (direction: {direction}, limit: {limit})")
                    for i, cid in enumerate(chat_ids, 1):
                        print(f"Syncing chat {i}/{len(chat_ids)}: {cid}")
                        await sync_dialog_messages(client, conn, telegram_account_id, cid, direction=direction, limit=limit)
                        # Small delay between chats to avoid rate limiting
                        if i < len(chat_ids):
                            await asyncio.sleep(0.5)
                else:
                    print(f"No chats found for account {telegram_account_id}. Please run sync_chats.py first.")
    except Exception as e:
        print(f"Error in fetch_and_sync_messages for session {session_file}: {e}")
        import traceback
        traceback.print_exc()

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
