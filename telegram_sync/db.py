import asyncpg
import os
import logging

async def get_db():
    import telegram_sync.config as config
    conn = await asyncpg.connect(dsn=config.POSTGRES_DSN)
    return conn

async def upsert_chat(conn, telegram_account_id, chat, full_photo_url=None, gender=None, age=None, last_seen=None):
    logging.info(f"Upserting chat for account {telegram_account_id}: {chat.name}")
    import datetime

    # Convert last_seen to datetime if it's a string
    if isinstance(last_seen, str):
        try:
            last_seen = datetime.datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        except Exception:
            last_seen = None

    await conn.execute(
        """
        INSERT INTO telegram_chats (id, telegram_account_id, name, type, username, unread_count, photo, last_message_id, last_message_time, gender, age, last_seen)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (id, telegram_account_id)
        DO UPDATE SET name = EXCLUDED.name, type = EXCLUDED.type, username = EXCLUDED.username, unread_count = EXCLUDED.unread_count, photo = EXCLUDED.photo, last_message_id = EXCLUDED.last_message_id, last_message_time = EXCLUDED.last_message_time, gender = EXCLUDED.gender, age = EXCLUDED.age, last_seen = EXCLUDED.last_seen
        """,
        chat.id,
        telegram_account_id,
        chat.name,
        "channel" if chat.is_channel else "group" if chat.is_group else "private" if chat.is_user else "bot" if chat.is_bot else "unknown",
        getattr(chat.entity, "username", None),
        chat.unread_count,
        full_photo_url,
        getattr(chat.message, "id", None),
        getattr(chat.message, "date", None),
        str(gender) if gender is not None else None,
        str(age) if age is not None else None,
        last_seen
    )
    # No need to commit with asyncpg; it auto-commits unless in a transaction

async def get_telegram_account_id(conn, session_file):
    result = await conn.fetchrow(
        """
        SELECT * FROM telegram_accounts WHERE session_file = $1
        """,
        os.path.basename(session_file)
    )
    return result['id'] if result else None 

async def upsert_telegram_account(conn, session_file, me, counts=0, full_photo_url=None):
    await conn.execute(
        """
        INSERT INTO telegram_accounts (id, session_file, phone, username, first_name, last_name, photo, unread_count)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (phone) DO UPDATE SET
            session_file = EXCLUDED.session_file,
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            photo = EXCLUDED.photo,
            unread_count = EXCLUDED.unread_count
        """,
        me.id,
        os.path.basename(session_file),
        me.phone,
        me.username,
        me.first_name,
        me.last_name,
        full_photo_url,
        counts,
    )

async def check_age_and_gender_already_set(conn, telegram_account_id):
    result = await conn.fetchrow(
        """
        SELECT * FROM telegram_chats WHERE id = $1 AND age IS NOT NULL AND gender IS NOT NULL
        """,
        telegram_account_id
    )
    return result is not None

async def get_age_and_gender_already_set(conn, telegram_account_id):
    result = await conn.fetchrow(
        """
        SELECT age, gender FROM telegram_chats WHERE id = $1 AND age IS NOT NULL AND gender IS NOT NULL
        """,
        telegram_account_id
    )
    return result if result else None

async def get_chat_ids_from_telegram_chat(conn, telegram_account_id):
    result = await conn.fetch(
        """
        SELECT id FROM telegram_chats WHERE telegram_account_id = $1 AND type = $2
        """,
        telegram_account_id,
        "private"
    )
    return [row['id'] for row in result] if result else []

# Utility functions for state management
async def get_last_synced_message(conn, telegram_account_id, chat_id, newest=True):
    column = "last_message_id" if newest else "oldest_message_id"
    result = await conn.fetchrow(
        f"SELECT {column} FROM telegram_sync_state WHERE chat_id=$1 AND telegram_account_id=$2",
        chat_id, telegram_account_id
    )
    return result[column] if result else None

async def set_last_synced_message(conn, telegram_account_id, chat_id, message_id, message_time, newest=True):
    # Normalize datetime
    if message_time is not None and message_time.tzinfo is not None:
        message_time = message_time.astimezone(tz=None).replace(tzinfo=None)

    # Update telegram_chats
    chat_column_id = "last_message_id" if newest else "oldest_message_id"
    chat_column_time = "last_message_time" if newest else "oldest_message_time"
    await conn.execute(
        f"""
        UPDATE telegram_chats SET {chat_column_id} = $1, {chat_column_time} = $4
        WHERE id = $2 AND telegram_account_id = $3
        """,
        message_id, chat_id, telegram_account_id, message_time
    )

    # Upsert telegram_sync_state
    state_column = "last_message_id" if newest else "oldest_message_id"
    await conn.execute(
        f"""
        INSERT INTO telegram_sync_state (chat_id, telegram_account_id, {state_column})
        VALUES ($1, $2, $3)
        ON CONFLICT (chat_id, telegram_account_id) DO UPDATE SET {state_column} = EXCLUDED.{state_column}
        """,
        chat_id, telegram_account_id, message_id
    )

async def upsert_message(conn, telegram_account_id, chat_id, message):
    # Ensure the date is naive (UTC) for PostgreSQL
    print(f"Upserting message ID {message.id} in chat ID {chat_id} for account {telegram_account_id}")
    msg_date = message.date
    if msg_date is not None and msg_date.tzinfo is not None:
        msg_date = msg_date.astimezone(tz=None).replace(tzinfo=None)
    await conn.execute(
        """
        INSERT INTO telegram_messages (chat_id, telegram_account_id, message_id, sender_id, text, date)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (chat_id, telegram_account_id, message_id)
        DO UPDATE SET text = EXCLUDED.text, sender_id = EXCLUDED.sender_id, date = EXCLUDED.date
        """,
        chat_id,
        telegram_account_id,
        message.id,
        getattr(message, 'sender_id', None),
        message.text,
        msg_date
    )