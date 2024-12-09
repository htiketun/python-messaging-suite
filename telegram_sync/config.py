import os

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "2040"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627")
SESSION_FOLDER = os.getenv("TELEGRAM_SESSION_FOLDER", "./sessions")
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN", "postgresql://postgres:password@localhost:5432/python-messaging-suite"
)
MEDIA_BASE_PATH = os.getenv("MEDIA_BASE_PATH", "media/")# Commit 4: 2024-07-08T01:20:15
# Commit 15: 2024-08-02T18:34:23
# Commit 41: 2024-10-02T14:33:22
# Commit 70: 2024-12-09T11:53:26
