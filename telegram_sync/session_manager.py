import os
from telethon import TelegramClient
import telegram_sync.config as config

def get_session_files(filename=None):
    """
    Returns a list of session file paths.
    If filename is provided, returns the path for that file if it exists.
    Otherwise, returns all session files in the session folder.
    """
    os.makedirs(config.SESSION_FOLDER, exist_ok=True)
    if filename:
        if isinstance(filename, list):
            filename = filename[0] if filename else None
        if filename:
            path = os.path.join(config.SESSION_FOLDER, filename)
            return [os.path.relpath(path)]
    return [
        os.path.join(config.SESSION_FOLDER, f)
        for f in os.listdir(config.SESSION_FOLDER)
        if f.endswith('.session')
    ]

def session_path(username):
    """
    Returns the full path for a user's session file.
    """
    os.makedirs(config.SESSION_FOLDER, exist_ok=True)
    return os.path.join(config.SESSION_FOLDER, f"{username}.session")

def new_session(username):
    """
    Creates and returns a new TelegramClient session for the given username.
    """
    return TelegramClient(
        session_path(username),
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH
    )