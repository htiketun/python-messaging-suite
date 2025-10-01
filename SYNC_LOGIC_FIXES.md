# Telegram Message Sync Logic Fixes

## Issues Fixed

### 1. **Message Ordering Confusion** ❌ → ✅

**Problem**: The original code assumed `messages[0]` was the oldest message, but `client.iter_messages()` returns messages from **newest to oldest**.

**Fix**:

-   `messages[0]` = **newest message**
-   `messages[-1]` = **oldest message**
-   Corrected the sync boundary tracking accordingly

### 2. **Wrong Sync State Tracking** ❌ → ✅

**Problem**: The code was setting newest/oldest boundaries incorrectly.

**Fix**:

```python
# BEFORE (Wrong)
await db.set_last_synced_message(conn, telegram_account_id, dialog_id, messages[0].id, messages[0].date, newest=True)  # oldest ❌
await db.set_last_synced_message(conn, telegram_account_id, dialog_id, messages[-1].id, messages[-1].date, newest=False)  # newest ❌

# AFTER (Correct)
newest_msg = messages[0]  # First = newest ✅
oldest_msg = messages[-1]  # Last = oldest ✅
await db.set_last_synced_message(conn, telegram_account_id, dialog_id, newest_msg.id, newest_msg.date, newest=True)
await db.set_last_synced_message(conn, telegram_account_id, dialog_id, oldest_msg.id, oldest_msg.date, newest=False)
```

### 3. **Incorrect "New" Direction Logic** ❌ → ✅

**Problem**: Used `newest=True` parameter incorrectly - should get the newest synced message ID to fetch newer messages.

**Fix**:

```python
# Get the newest synced message ID, then fetch messages newer than that
newest_synced_id = await db.get_last_synced_message(conn, telegram_account_id, dialog_id, newest=True)
async for msg in client.iter_messages(dialog_id, min_id=newest_synced_id):
    # Process new messages...
```

### 4. **Problematic "Old" Direction Logic** ❌ → ✅

**Problem**: The reverse parameter and max_id usage was incorrect.

**Fix**:

```python
# Get messages older than the oldest synced message
oldest_synced_id = await db.get_last_synced_message(conn, telegram_account_id, dialog_id, newest=False)
async for msg in client.iter_messages(dialog_id, max_id=oldest_synced_id, limit=limit):
    # max_id excludes that message ID, so we get older messages
    # messages are still newest-first, so last message is oldest
```

### 5. **Improved Error Handling** 🆕

**Added**:

-   Specific error handling for common Telegram errors
-   Flood wait retry logic
-   Better logging and progress tracking
-   Rate limiting between chats
-   Detailed error messages with stack traces

## How The Fixed Logic Works

### "latest" Direction

1. Fetch the latest N messages (newest to oldest)
2. Insert all messages into database
3. Set sync boundaries: newest = first message, oldest = last message

### "new" Direction

1. Get the newest synced message ID from database
2. Fetch messages newer than that ID using `min_id`
3. Update the newest sync boundary with the newest new message

### "old" Direction

1. Get the oldest synced message ID from database
2. Fetch messages older than that ID using `max_id`
3. Update the oldest sync boundary with the oldest new message

## Key Concepts

-   **`min_id`**: Get messages with ID > min_id (newer messages)
-   **`max_id`**: Get messages with ID < max_id (older messages)
-   **`iter_messages()`** always returns newest → oldest unless `reverse=True`
-   **Sync boundaries** track the newest and oldest message IDs we've synced

## Usage Examples

```bash
# Sync latest 50 messages for all chats
python sync_messages.py --direction latest --limit 50

# Sync new messages for specific chat
python sync_messages.py --chat_id 123456 --direction new

# Sync older messages (pagination backwards)
python sync_messages.py --direction old --limit 100

# Use specific session file
python sync_messages.py --session_file path/to/session.session --direction latest
```

## Error Handling Improvements

-   **FloodWaitError**: Automatically waits and retries
-   **ChatAdminRequiredError**: Skips private chats gracefully
-   **ChannelPrivateError**: Handles inaccessible channels
-   **PeerIdInvalidError**: Skips invalid chat IDs
-   **Progress logging**: Shows sync progress and statistics
-   **Rate limiting**: 0.5s delay between chats to avoid rate limits
