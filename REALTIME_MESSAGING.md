# Real-time Telegram Messaging System

## Overview

This system provides real-time monitoring and streaming of Telegram messages using WebSocket connections. It allows you to receive new messages and message edits as they happen in your monitored Telegram chats.

## Architecture

```
Telegram API ←→ Telethon Client ←→ RealTimeMessageService ←→ WebSocket ←→ Frontend
                      ↓
                 Database (SQLite)
```

## Components

### 1. **RealTimeMessageService** (`telegram_sync/realtime_messages.py`)

Core service that manages Telegram client connections and event handling.

**Features:**

-   Monitors multiple Telegram sessions simultaneously
-   Handles new messages and message edits
-   Manages WebSocket connections
-   Automatically saves messages to database
-   Supports selective chat monitoring

### 2. **Real-time API** (`telegram_sync/realtime_api.py`)

FastAPI endpoints for controlling the real-time service.

**Endpoints:**

-   Start/stop monitoring sessions
-   Add/remove chats from monitoring
-   Get monitoring status
-   WebSocket connection for real-time data

### 3. **WebSocket Integration** (`telegram_sync/api_sync.py`)

Integrated with the main FastAPI application.

## API Endpoints

### Start Monitoring

```bash
POST /realtime/start-monitoring/
{
    "session_file": "path/to/session.session",
    "chat_ids": [123456, 789012]  // optional
}
```

### Stop Monitoring

```bash
POST /realtime/stop-monitoring/
{
    "session_file": "path/to/session.session"
}
```

### Get Status

```bash
GET /realtime/status/
```

Returns current monitoring status and active connections.

### Add Chat to Monitoring

```bash
POST /realtime/add-chat/
{
    "session_file": "path/to/session.session",
    "chat_id": 123456
}
```

### Remove Chat from Monitoring

```bash
POST /realtime/remove-chat/
{
    "session_file": "path/to/session.session",
    "chat_id": 123456
}
```

### WebSocket Connection

```
ws://localhost:8000/ws/messages
```

## WebSocket Message Format

### New Message

```json
{
    "type": "new_message",
    "session_file": "session.session",
    "chat_id": 123456,
    "message_id": 789,
    "date": "2025-10-01T10:30:00",
    "text": "Hello world",
    "sender": {
        "id": 111,
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe"
    },
    "chat": {
        "id": 123456,
        "title": "Group Chat",
        "username": "groupchat",
        "type": "group"
    },
    "media": false,
    "timestamp": "2025-10-01T10:30:01"
}
```

### Edited Message

```json
{
    "type": "message_edited",
    "session_file": "session.session",
    "chat_id": 123456,
    "message_id": 789,
    "date": "2025-10-01T10:30:00",
    "text": "Hello world (edited)",
    "sender": {
        "id": 111,
        "first_name": "John",
        "username": "johndoe"
    },
    "timestamp": "2025-10-01T10:31:00"
}
```

### System Messages

```json
{
    "type": "connection_established",
    "message": "Connected to real-time message stream",
    "timestamp": "now"
}
```

## Usage Examples

### 1. Start Monitoring All Chats

```bash
curl -X POST "http://localhost:8000/realtime/start-monitoring/" \
  -H "Content-Type: application/json" \
  -d '{"session_file": "sessions/user1.session"}'
```

### 2. Start Monitoring Specific Chats

```bash
curl -X POST "http://localhost:8000/realtime/start-monitoring/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_file": "sessions/user1.session",
    "chat_ids": [123456, 789012, -100123456]
  }'
```

### 3. WebSocket Connection (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/messages');

ws.onmessage = function (event) {
    const data = JSON.parse(event.data);

    if (data.type === 'new_message') {
        console.log('New message:', data.text);
        console.log('From:', data.sender.first_name);
        console.log('Chat:', data.chat.title);
    }
};

// Send ping to keep connection alive
ws.send(JSON.stringify({ type: 'ping' }));
```

### 4. Check Status

```bash
curl -X GET "http://localhost:8000/realtime/status/"
```

### 5. Stop Monitoring

```bash
curl -X POST "http://localhost:8000/realtime/stop-monitoring/" \
  -H "Content-Type: application/json" \
  -d '{"session_file": "sessions/user1.session"}'
```

## Running the System

### 1. Start FastAPI Server

```bash
uvicorn telegram_sync.api_sync:app --reload --host 0.0.0.0 --port 8000
```

### 2. Test with HTML Client

Open `realtime_test.html` in your browser and:

1. Click "Connect" to establish WebSocket connection
2. Enter session file path and optional chat IDs
3. Click "Start Monitoring" to begin real-time monitoring
4. Watch messages appear in real-time

### 3. Integration with Frontend

Connect your Vue.js/React frontend to the WebSocket endpoint for real-time message display.

## Features

### ✅ **Implemented**

-   Real-time new message detection
-   Real-time message edit detection
-   Multiple session monitoring
-   Selective chat monitoring
-   WebSocket broadcasting
-   Automatic database persistence
-   Connection management
-   Error handling and recovery
-   Flood wait handling

### 🔄 **Advanced Features**

-   Message read status updates
-   Typing indicators
-   File/media message handling
-   Message reactions
-   User status changes
-   Chat member updates

## Error Handling

The system handles various Telegram API errors:

-   **FloodWaitError**: Automatic retry after wait period
-   **ChatAdminRequiredError**: Skip private chats
-   **ChannelPrivateError**: Skip inaccessible channels
-   **PeerIdInvalidError**: Skip invalid chat IDs
-   **Connection errors**: Automatic reconnection attempts

## Performance Considerations

-   Uses async/await for non-blocking operations
-   Efficient event-driven architecture
-   Minimal memory footprint per connection
-   Rate limiting to avoid Telegram API limits
-   Connection pooling for multiple sessions

## Security Notes

-   Session files contain authentication tokens
-   Ensure proper file permissions on session files
-   Use HTTPS/WSS in production
-   Implement authentication for API endpoints
-   Validate session file paths to prevent directory traversal

## Testing

1. **Unit Tests**: Test individual components
2. **Integration Tests**: Test API endpoints
3. **WebSocket Tests**: Test real-time functionality
4. **Load Tests**: Test multiple concurrent connections

## Deployment

### Development

```bash
uvicorn telegram_sync.api_sync:app --reload --port 8000
```

### Production

```bash
gunicorn telegram_sync.api_sync:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4
```

Use nginx as reverse proxy for WebSocket support and SSL termination.
