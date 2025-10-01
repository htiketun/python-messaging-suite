# Real-Time Chat List Implementation

This document outlines the implementation of real-time chat list functionality in the messaging suite.

## Overview

The real-time chat list system monitors Telegram chats and broadcasts updates to connected clients via WebSocket. It provides live updates for:

-   New messages affecting chat order
-   User online/offline status changes
-   Unread message count updates
-   Chat metadata changes (name, photo, etc.)
-   New chats being added

## Architecture

### Backend Components

1. **RealtimeChatListService** (`telegram_sync/realtime_chat_list.py`)

    - Core service managing WebSocket connections and Telegram monitoring
    - Handles Telethon event listeners for chat updates
    - Broadcasts updates to connected clients

2. **FastAPI WebSocket Endpoints** (`telegram_sync/api_sync.py`)
    - `/ws/chat-list` - WebSocket endpoint for real-time chat list updates
    - `/realtime/start-chat-list-monitoring/` - Start monitoring a session
    - `/realtime/stop-chat-list-monitoring/` - Stop monitoring a session
    - `/realtime/chat-list-status/` - Get monitoring status

### Frontend Components

1. **ChatSidebar.vue** - Updated with real-time functionality
    - WebSocket connection management
    - Real-time chat list updates
    - Connection status indicator
    - Auto-reconnection logic

## Usage

### Starting Real-Time Monitoring

```bash
# Start chat list monitoring for a session
curl -X POST "http://localhost:8000/realtime/start-chat-list-monitoring/" \
  -d "session_file=path/to/session.session"
```

### WebSocket Connection

```javascript
// Connect to chat list WebSocket
const socket = new WebSocket('ws://localhost:8000/ws/chat-list');

// Request current chat list
socket.send(
    JSON.stringify({
        type: 'get_chat_list',
        session_file: 'path/to/session.session',
    }),
);
```

### Message Types

#### Incoming Messages (Server → Client)

1. **chat_list_initial** - Initial chat list when monitoring starts

```json
{
    "type": "chat_list_initial",
    "session_file": "session.session",
    "chats": [...],
    "timestamp": "2024-01-01T12:00:00"
}
```

2. **chat_list_update** - Single chat update (new message)

```json
{
    "type": "chat_list_update",
    "session_file": "session.session",
    "chat_id": 123456,
    "last_message": {
        "id": 789,
        "text": "Hello world",
        "date": "2024-01-01T12:00:00",
        "from_me": false
    },
    "timestamp": "2024-01-01T12:00:00"
}
```

3. **user_status_update** - User online/offline status change

```json
{
    "type": "user_status_update",
    "session_file": "session.session",
    "user_id": 123456,
    "status": {
        "type": "online"
    },
    "timestamp": "2024-01-01T12:00:00"
}
```

4. **unread_count_update** - Unread message count change

```json
{
    "type": "unread_count_update",
    "session_file": "session.session",
    "chat_id": 123456,
    "max_id": 789,
    "timestamp": "2024-01-01T12:00:00"
}
```

#### Outgoing Messages (Client → Server)

1. **get_chat_list** - Request current chat list

```json
{
    "type": "get_chat_list",
    "session_file": "session.session"
}
```

2. **ping** - Heartbeat/keep-alive

```json
{
    "type": "ping"
}
```

## Vue.js Integration

### Key Features

1. **Real-time Connection Status**

    - Visual indicator showing connection state
    - Reconnect button when disconnected
    - Auto-reconnection logic

2. **Live Chat Updates**

    - Automatic chat list refresh on new messages
    - Chat reordering based on message timestamps
    - Online status updates in real-time

3. **Session Management**
    - Automatic monitoring start/stop based on selected account
    - Proper cleanup on component unmount
    - Session switching support

### Implementation Details

```vue
<script setup>
// WebSocket connection for real-time chat list
let chatListSocket = null;
const isRealtimeConnected = ref(false);

function setupRealtimeChatListWebSocket() {
    chatListSocket = new WebSocket(`${socketUrl}chat-list`);

    chatListSocket.onopen = () => {
        isRealtimeConnected.value = true;
        // Request initial data and start monitoring
        chatListSocket.send(
            JSON.stringify({
                type: 'get_chat_list',
                session_file: props.chatAccountUser.session_file,
            }),
        );
        startChatListMonitoring();
    };

    chatListSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // Handle different message types
        if (data.type === 'chat_list_initial') {
            handleChatListUpdate(data.chats);
        } else if (data.type === 'chat_list_update') {
            handleSingleChatUpdate(data);
        }
        // ... handle other message types
    };
}
</script>
```

## Event Handling

### Telethon Event Listeners

1. **UserUpdate Events** - Track user status changes
2. **NewMessage Events** - Update chat list order and last message
3. **MessageRead Events** - Update unread counts

### Vue.js Event Handlers

1. **handleChatListUpdate()** - Process full chat list updates
2. **handleSingleChatUpdate()** - Process individual chat updates
3. **handleUserStatusUpdate()** - Update user online status
4. **handleUnreadCountUpdate()** - Update unread message counts

## Connection Management

### Auto-Reconnection

-   Automatically reconnects after 3 seconds on disconnect
-   Restarts monitoring when reconnecting
-   Maintains session state across reconnections

### Error Handling

-   Graceful handling of WebSocket errors
-   Fallback to API calls if WebSocket fails
-   User feedback for connection issues

## Performance Considerations

1. **Event Filtering** - Only broadcast relevant updates
2. **Connection Limits** - Manage WebSocket connection pool
3. **Memory Management** - Proper cleanup of event listeners
4. **Batching** - Group multiple updates when possible

## Testing

### Manual Testing

1. Start FastAPI server with `uvicorn telegram_sync.api_sync:app --host 0.0.0.0 --port 8000`
2. Open Vue.js application
3. Connect with a Telegram account
4. Send messages from another client
5. Verify real-time updates appear in chat list

### WebSocket Testing

```bash
# Test WebSocket connection
wscat -c ws://localhost:8000/ws/chat-list

# Send test message
{"type": "ping"}
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**

    - Check if FastAPI server is running
    - Verify port 8000 is not blocked
    - Check browser console for errors

2. **No Real-time Updates**

    - Verify session file is valid and authorized
    - Check if monitoring was started successfully
    - Look for Telethon event handler errors in logs

3. **High Memory Usage**
    - Monitor WebSocket connection count
    - Check for proper cleanup on disconnect
    - Review event listener management

### Debug Commands

```bash
# Check monitoring status
curl http://localhost:8000/realtime/chat-list-status/

# Start monitoring manually
curl -X POST "http://localhost:8000/realtime/start-chat-list-monitoring/" \
  -d "session_file=sessions/session.session"
```

## Future Enhancements

1. **Chat Typing Indicators** - Show when users are typing
2. **Message Reactions** - Real-time reaction updates
3. **Group Chat Members** - Live member status updates
4. **Push Notifications** - Browser notifications for new messages
5. **Offline Queue** - Store updates when disconnected and sync on reconnect

## Security Considerations

1. **Session Validation** - Verify session ownership before monitoring
2. **Rate Limiting** - Prevent WebSocket spam
3. **Authentication** - Secure WebSocket connections
4. **Data Sanitization** - Clean message content before broadcasting
