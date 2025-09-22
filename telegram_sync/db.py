import asyncpg
import os
import logging

async def get_db():
    import telegram_sync.config as config
    conn = await asyncpg.connect(dsn=config.POSTGRES_DSN)
    return conn

async def upsert_chat(conn, session, chat):
    logging.info(f"Upserting chat for session {session}: {chat.name}")
  
    await conn.execute(
        """
        INSERT INTO telegram_chats (id, session, name, type, username)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id, session)
        DO UPDATE SET name = EXCLUDED.name, type = EXCLUDED.type, username = EXCLUDED.username
        """,
        chat.id,
        session,
        chat.name,
        "channel" if chat.is_channel else "group" if chat.is_group else "private" if chat.is_user else "bot" if chat.is_bot else "unknown",
        getattr(chat.entity, "username", None)
    )
    # No need to commit with asyncpg; it auto-commits unless in a transaction


async def upsert_telegram_account(conn, session_file, me):
    logging.info(f"Upserting account for session {session_file}: {me.username}")
    logging.debug(f"Account details: {me}")
    await conn.execute(
        """
        INSERT INTO telegram_accounts (session_file, phone, username, first_name, photo)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (session_file) DO UPDATE SET
            phone = EXCLUDED.phone,
            username = EXCLUDED.username,
            first_name = EXCLUDED.first_name,
            photo = EXCLUDED.photo
        """,
        os.path.basename(session_file),
        me.phone,
        me.username,
        me.first_name,
        (me.photo and str(me.photo)) or None
    )


# Utility functions for state management
async def get_last_synced_message(conn, session, chat_id, newest=True):
    column = "last_message_id" if newest else "oldest_message_id"
    result = await conn.fetchrow(
        f"SELECT {column} FROM telegram_sync_state WHERE chat_id=$1 AND session=$2",
        chat_id, session
    )
    return result[column] if result else None

async def set_last_synced_message(conn, session, chat_id, message_id, message_time, newest=True):
    # Normalize datetime
    if message_time is not None and message_time.tzinfo is not None:
        message_time = message_time.astimezone(tz=None).replace(tzinfo=None)

    # Update telegram_chats
    chat_column_id = "last_message_id" if newest else "oldest_message_id"
    chat_column_time = "last_message_time" if newest else "oldest_message_time"
    await conn.execute(
        f"""
        UPDATE telegram_chats SET {chat_column_id} = $1, {chat_column_time} = $4
        WHERE id = $2 AND session = $3
        """,
        message_id, chat_id, session, message_time
    )

    # Upsert telegram_sync_state
    state_column = "last_message_id" if newest else "oldest_message_id"
    await conn.execute(
        f"""
        INSERT INTO telegram_sync_state (chat_id, session, {state_column})
        VALUES ($1, $2, $3)
        ON CONFLICT (chat_id, session) DO UPDATE SET {state_column} = EXCLUDED.{state_column}
        """,
        chat_id, session, message_id
    )

async def upsert_message(conn, session, chat_id, message):
    # Ensure the date is naive (UTC) for PostgreSQL
    print(f"Upserting message ID {message.id} in chat ID {chat_id} for session {session}")
    msg_date = message.date
    if msg_date is not None and msg_date.tzinfo is not None:
        msg_date = msg_date.astimezone(tz=None).replace(tzinfo=None)
    await conn.execute(
        """
        INSERT INTO telegram_messages (chat_id, session, message_id, sender_id, text, date)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (chat_id, session, message_id)
        DO UPDATE SET text = EXCLUDED.text, sender_id = EXCLUDED.sender_id, date = EXCLUDED.date
        """,
        chat_id,
        session,
        message.id,
        getattr(message, 'sender_id', None),
        message.text,
        msg_date
    )