import os

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "20724149"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "d919f276e10b80ab0b5bf4dad0121663")
SESSION_FOLDER = os.getenv("TELEGRAM_SESSION_FOLDER", "./sessions")
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN", "postgresql://postgres:password@localhost:5432/python-messaging-suite"
)
MEDIA_BASE_PATH = os.getenv("MEDIA_BASE_PATH", "media/")