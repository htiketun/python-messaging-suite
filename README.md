# Python Messaging Suite

A modular, async-ready messaging suite for Telegram, built with Django, FastAPI, Telethon, and Django REST Framework.

---

## Features

-   **Telegram Sync**: Sync chats and messages from Telegram accounts using Telethon.
-   **REST API**: Django REST Framework endpoints for listing chats, chat details, paginated messages, and sending messages.
-   **FastAPI**: Async API endpoints for triggering Telegram sync and message operations.
-   **WebSocket**: (Optional) Real-time communication support via FastAPI.
-   **Admin Panel**: Manage users, chats, and messages via Django admin.
-   **Logging**: All sync and message operations are logged for auditing.
-   **Gender Detection**: Guess user gender using `gender-guesser` and optionally AI/transformers.
-   **Session Management**: Handles multiple Telegram accounts via session files.
-   **Pagination**: Paginated message listing for efficient frontend consumption.
-   **Extensible Models**: Modular Django models for accounts, chats, messages, and more.

---

## Project Structure

```
python-messaging-suite/
├── api/                        # Django app: models, serializers, views, urls
│   ├── models/                 # Django models for Telegram entities
│   ├── serializers/            # DRF serializers for API
│   ├── views/                  # DRF views for API endpoints
│   ├── urls.py                 # DRF API URL routing
│   └── ...                     # Admin, tests, etc.
├── telegram_sync/              # Telegram sync logic, FastAPI endpoints, helpers
│   ├── sync_chats.py           # Sync Telegram chats
│   ├── sync_messages.py        # Sync Telegram messages
│   ├── api_sync.py             # FastAPI endpoints for sync
│   ├── db.py                   # Async DB helpers
│   ├── session_manager.py      # Session file management
│   ├── telegram_checker.py     # Gender and profile analysis
│   └── ...                     # Other helpers
├── python-messaging-suite/     # Django project root
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Django URLs
│   ├── asgi.py                 # ASGI entrypoint (for FastAPI & Django)
│   └── wsgi.py                 # WSGI entrypoint (for Django)
└── ...
```

---

## Setup

### 1. **Install dependencies**

```sh
pip install -r requirements.txt
# Or manually:
pip install django djangorestframework django-cors-headers djangorestframework-simplejwt fastapi uvicorn websockets wsproto telethon psycopg2-binary gender-guesser name-dataset
```

### 2. **Configure environment**

-   Set your Telegram API credentials in `telegram_sync/config.py`:
    ```python
    TELEGRAM_API_ID = "your_api_id"
    TELEGRAM_API_HASH = "your_api_hash"
    SESSION_FOLDER = "path/to/session/folder"
    ```
-   Set Django settings in `python-messaging-suite/settings.py` (including database, REST_FRAMEWORK, etc).

### 3. **Run Django migrations**

```sh
python manage.py migrate
```

### 4. **Create a superuser (for admin panel)**

```sh
python manage.py createsuperuser
```

### 5. **Run Django server (REST API & admin)**

```sh
python manage.py runserver
```

### 6. **Run FastAPI server (for async sync APIs)**

```sh
uvicorn telegram_sync.api_sync:app --reload
```

---

## API Endpoints

### **Django REST API**

-   **List all chats:**  
    `GET /api/chats/`
-   **Chat detail:**  
    `GET /api/chats/<chat_id>/`
-   **Paginated messages for a chat:**  
    `GET /api/chats/<chat_id>/messages/?page=1&page_size=20`
-   **Send a message:**  
    `POST /api/chats/<chat_id>/send/<telegram_account_id>/`  
    Body: `{"text": "Hello from API"}`

### **FastAPI Endpoints**

-   **Sync Telegram chats:**  
    `POST /telegram-chats/?session_file=path/to/session.session`
-   **Sync Telegram messages:**  
    `POST /telegram-messages/`  
    Body: `{"session_file": "path/to/session.session", "chat_id": 123456, "direction": "new", "limit": 100}`

### **WebSocket Example**

-   **Echo WebSocket:**  
    `ws://localhost:8000/ws/echo`  
    (See `api_sync.py` for example)

---

## Usage Examples

**Sync Telegram Chats:**

```sh
curl -X POST "http://localhost:8000/telegram-chats/?session_file=path/to/session.session"
```

**Sync Telegram Messages:**

```sh
curl -X POST "http://localhost:8000/telegram-messages/" \
  -H "Content-Type: application/json" \
  -d '{"session_file": "path/to/session.session", "chat_id": 123456, "direction": "new", "limit": 100}'
```

**Send Telegram Message:**

```sh
curl -X POST "http://localhost:8000/api/chats/<chat_id>/send/<telegram_account_id>/" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from API"}'
```

---

## Production Deployment

-   **FastAPI:**
    ```sh
    gunicorn telegram_sync.api_sync:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4
    ```
-   **Django:**  
    Use Gunicorn or uWSGI for production.
-   **Reverse Proxy:**  
    Use nginx or Caddy for SSL and performance.
-   **Process Manager:**  
    Use systemd or supervisor to keep your app running.

---

## Developer Notes

-   **Session Files:**  
    Telegram session files are required for each account. Place them in the configured session folder.
-   **Logging:**  
    Check `chats.log` and `send_message.log` for operation logs.
-   **Gender Detection:**  
    Uses `gender-guesser` and optionally transformers for AI-based guessing.
-   **Pagination:**  
    Message list endpoints are paginated (see `TelegramMessagePagination`).
-   **WebSocket:**  
    Example endpoint in `api_sync.py` for real-time features.
-   **Error Handling:**  
    All API endpoints return clear error messages and log failures.
-   **Extensible:**  
    Add new models, endpoints, or sync logic as needed.

---

## License

MIT

---

## Credits

-   [Django](https://www.djangoproject.com/)
-   [Django REST Framework](https://www.django-rest-framework.org/)
-   [FastAPI](https://fastapi.tiangolo.com/)
-   [Telethon](https://docs.telethon.dev/)
-   [gender-guesser](https://pypi.org/project/gender-guesser/)
-   [transformers](https://huggingface.co/docs/transformers/index)


 <!-- python -m telegram_sync.sync_messages --direction=old -->
Update 2024-07-01T00:57:27 

Update 2024-07-05T16:33:46 

Update 2024-07-10T09:27:02 

Update 2024-07-12T17:38:35 

Update 2024-07-15T01:11:54 

Update 2024-07-17T10:04:13 

Update 2024-07-19T17:49:11 

Update 2024-07-22T01:38:21 

Update 2024-07-29T02:02:08 

Update 2024-07-31T10:28:41 

Update 2024-08-05T02:32:10 

Update 2024-08-07T10:37:01 

Update 2024-08-09T19:36:31 

Update 2024-08-12T03:14:58 

Update 2024-08-14T11:48:45 

Update 2024-08-16T19:22:26 

Update 2024-08-21T12:02:57 

Update 2024-08-26T04:35:55 

Update 2024-08-28T12:14:48 

Update 2024-09-02T04:45:46 

Update 2024-09-04T13:05:12 

Update 2024-09-06T20:45:51 

Update 2024-09-13T21:25:53 

Update 2024-09-16T06:15:01 

Update 2024-09-23T06:11:30 

Update 2024-09-25T14:22:42 

Update 2024-09-30T06:26:58 

Update 2024-10-02T14:33:22 

Update 2024-10-04T22:40:59 

Update 2024-10-07T07:13:14 

Update 2024-10-09T15:24:56 

Update 2024-10-14T07:14:41 

Update 2024-10-16T16:06:43 

Update 2024-10-21T08:17:03 

Update 2024-10-23T16:11:55 

Update 2024-10-28T08:53:18 

Update 2024-10-30T16:54:30 

Update 2024-11-02T01:00:51 

Update 2024-11-06T17:33:54 

Update 2024-11-09T01:43:45 

Update 2024-11-13T18:01:34 

Update 2024-11-16T01:51:16 

Update 2024-11-18T10:05:11 

Update 2024-11-23T02:15:30 

Update 2024-11-25T10:23:32 

Update 2024-12-02T10:49:42 

Update 2024-12-04T19:08:15 

Update 2024-12-07T03:51:05 

Update 2024-12-11T19:38:48 

Update 2024-12-16T12:24:09 

Update 2024-12-21T04:46:55 

Update 2024-12-25T20:13:50 

Update 2025-01-01T21:31:35 

Update 2025-01-04T05:14:17 

Update 2025-01-06T13:20:02 

Update 2025-01-08T21:31:55 

Update 2025-01-13T14:01:01 

Update 2025-01-20T14:32:29 

Update 2025-01-25T06:25:41 

Update 2025-01-27T14:30:37 

Update 2025-01-29T23:33:09 

Update 2025-02-10T15:30:34 

Update 2025-02-12T23:44:58 

Update 2025-02-15T08:34:48 

Update 2025-02-22T08:29:48 

Update 2025-02-24T16:58:47 

Update 2025-03-01T08:44:52 

Update 2025-03-03T16:58:21 

Update 2025-03-06T01:39:27 

Update 2025-03-10T17:37:22 

Update 2025-03-15T10:20:33 

Update 2025-03-20T02:28:47 

Update 2025-03-22T10:06:17 

Update 2025-03-27T03:06:01 

Update 2025-03-31T18:58:29 

Update 2025-04-05T11:49:29 

Update 2025-04-17T03:55:27 

Update 2025-04-19T12:42:18 

Update 2025-04-21T20:57:41 

Update 2025-04-26T13:13:29 

Update 2025-04-28T20:45:38 

Update 2025-05-01T05:43:44 

Update 2025-05-08T05:57:31 

Update 2025-05-10T13:52:21 

Update 2025-05-12T22:32:46 

Update 2025-05-15T05:49:27 

Update 2025-05-26T22:47:53 

Update 2025-05-31T15:21:25 

Update 2025-06-02T23:56:30 

Update 2025-06-10T00:08:21 

Update 2025-06-17T00:02:26 

Update 2025-06-19T08:18:12 

Update 2025-06-21T16:27:43 

Update 2025-06-26T09:32:13 

Update 2025-07-01T01:07:08 

Update 2025-07-03T09:49:31 

Update 2025-07-05T17:50:12 

Update 2025-07-08T01:48:02 

Update 2025-07-12T18:45:36 

Update 2025-07-15T02:22:16 

Update 2025-07-22T03:20:37 

Update 2025-07-26T18:53:00 

Update 2025-08-05T04:18:52 

Update 2025-08-07T12:15:15 

Update 2025-08-09T19:47:09 

Update 2025-08-16T20:58:24 

Update 2025-08-19T04:22:23 

Update 2025-08-21T12:32:35 

Update 2025-08-23T21:08:41 

Update 2025-08-26T04:52:11 

Update 2025-08-28T13:42:00 

Update 2025-08-30T21:25:38 

Update 2025-09-09T06:09:16 

Update 2025-09-11T14:25:06 

Update 2025-09-16T06:49:03 

Update 2025-09-18T15:20:14 

Update 2025-09-27T23:53:08 

Update 2025-09-30T07:42:53 

Update 2025-10-04T23:46:24 

Update 2025-10-07T07:52:06 

Update 2025-10-09T16:49:26 

Update 2024-07-03T08:44:39 

Update 2024-07-10T09:08:30 

Update 2024-07-29T02:19:00 

Update 2024-08-02T18:34:43 

Update 2024-08-14T11:44:44 

Update 2024-08-16T19:20:09 

Update 2024-08-19T04:19:49 

Update 2024-08-26T03:54:21 

Update 2024-08-28T12:39:13 

Update 2024-09-02T04:49:27 

Update 2024-09-04T12:51:38 

Update 2024-09-06T21:17:15 

Update 2024-09-09T05:13:13 

Update 2024-09-11T13:54:08 

Update 2024-09-13T21:07:32 

Update 2024-09-16T05:22:41 

Update 2024-09-18T14:24:09 

Update 2024-09-20T21:39:55 

Update 2024-09-27T22:13:05 

Update 2024-07-01T00:59:52 

Update 2024-07-05T16:33:33 

Update 2024-07-08T00:40:45 

Update 2024-07-10T08:38:51 

Update 2024-07-15T01:44:09 

Update 2024-07-17T09:16:08 

Update 2024-07-19T17:52:49 

Update 2024-07-22T01:43:57 

Update 2024-07-24T10:10:08 

Update 2024-07-26T18:22:46 

Update 2024-07-29T02:07:38 

Update 2024-07-31T10:45:37 

Update 2024-08-05T02:32:48 

Update 2024-08-09T19:02:13 

Update 2024-08-14T11:54:26 

Update 2024-08-19T03:32:26 

Update 2024-08-21T11:39:19 

Update 2024-08-23T20:40:40 

Update 2024-09-09T05:45:39 

Update 2024-09-11T13:04:27 

Update 2024-09-16T05:48:48 

Update 2024-09-18T13:40:17 

Update 2024-09-20T21:47:02 

Update 2024-09-23T06:01:58 
