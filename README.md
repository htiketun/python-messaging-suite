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
