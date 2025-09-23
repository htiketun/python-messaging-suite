import asyncio
import json
import os
import logging
from telethon import TelegramClient, errors
import telegram_sync.config as config
import telegram_sync.session_manager as sm
import telegram_sync.db as db
import gender_guesser.detector as gender
from telethon.tl.functions.users import GetFullUserRequest

# Setup logging
logging.basicConfig(
    filename='chats.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

def guess_gender(first_name):
    d = gender.Detector(case_sensitive=False)
    g = d.get_gender(first_name) if first_name else ""
    if g in ["male", "mostly_male"]:
        return "male"
    elif g in ["female", "mostly_female"]:
        return "female"
    return "unknown"

def build_me_dict(me, session_file):
    first_name = getattr(me, "first_name", "")
    return {
        "session_file": os.path.basename(session_file),
        "phone": getattr(me, "phone", ""),
        "app_id": config.TELEGRAM_API_ID,
        "app_hash": config.TELEGRAM_API_HASH,
        "sdk": "Windows 11",
        "app_version": "5.12.3 x64",
        "device": getattr(me, "device", "Unknown"),
        "device_model": getattr(me, "device_model", "Unknown"),
        "lang_pack": getattr(me, "lang_pack", "tdesktop"),
        "system_lang_pack": getattr(me, "system_lang_pack", "en-US"),
        "user_id": getattr(me, "id", ""),
        "username": getattr(me, "username", ""),
        "ipv6": False,
        "first_name": first_name,
        "last_name": getattr(me, "last_name", ""),
        "register_time": getattr(me, "date", "").isoformat() if getattr(me, "date", None) else "",
        "sex": guess_gender(first_name),
        "last_check_time": None,
        "device_token": "",
        "lang_code": getattr(me, "lang_code", "en"),
        "tz_offset": None,
        "perf_cat": None,
        "avatar": "",
        "proxy": None,
        "twoFA": "",
        "password": "",
        "block": False,
        "package_id": "",
        "installer": "",
        "system_lang_code": getattr(me, "system_lang_pack", "en-US"),
        "email": "",
        "email_id": "",
        "secret": "",
        "category": ""
    }

async def fetch_and_sync(session_file, conn):
    try:
        client = TelegramClient(session_file, config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            os.remove(session_file)
            msg = f"Session file {session_file} exists but Telegram session is unauthorized. Skipping."
            print(msg)
            logging.warning(msg)
            return

        me = await client.get_me()

        full = await client(GetFullUserRequest(me.username)) if me.username else None
        # Save the full user info as JSON for inspection
        session_dir = os.path.dirname(session_file)
        full_json_path = os.path.join(session_dir, os.path.basename(session_file) + ".full.json")
        import base64
        def convert_datetime(obj):
            if isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(i) for i in obj]
            elif isinstance(obj, bytes):
                # Convert bytes to base64 string for JSON serialization
                return base64.b64encode(obj).decode('utf-8')
            elif hasattr(obj, "isoformat") and callable(obj.isoformat):
                return obj.isoformat()
            else:
                return obj

        with open(full_json_path, "w", encoding="utf-8") as f:
            full_dict = full.to_dict() if full else {}
            json.dump(convert_datetime(full_dict), f, ensure_ascii=False, indent=4)
        session_dir = os.path.dirname(session_file)
        json_path = os.path.join(session_dir, os.path.basename(session_file) + ".json")
        me_dict = build_me_dict(me, session_file)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(me_dict, f, ensure_ascii=False, indent=4)

        msg = f"Syncing chats for: {me.username or me.phone}"
        print(msg)

        async for dialog in client.iter_dialogs():
            await db.upsert_chat(conn, os.path.basename(session_file), dialog)
            await db.upsert_telegram_account(conn, session_file, me)

        await asyncio.sleep(2)
        await client.disconnect()

    except errors.UnauthorizedError:
        try:
            await client.disconnect()
        except Exception:
            pass
        os.remove(session_file)
        msg = f"Session file {session_file} exists but Telegram session is unauthorized. Skipping."
        print(msg)
        logging.warning(msg)
    except Exception as e:
        msg = f"Error in fetch_and_sync for {session_file}: {e}"
        print(msg)
        logging.error(msg)

async def main(session_files=None):
    logging.info("Started sync_chats.py")
    if session_files is None:
        session_files = sm.get_session_files()
    if not session_files:
        msg = "No session files found. Use add_session.py first."
        print(msg)
        logging.warning(msg)
        return

    conn = await db.get_db()
    for sess in session_files:
        try:
            await fetch_and_sync(sess, conn)
        except errors.FloodWaitError as e:
            msg = f"FloodWait: Sleeping for {e.seconds} seconds..."
            print(msg)
            logging.warning(msg)
            await asyncio.sleep(e.seconds)
        except Exception as e:
            msg = f"Error with session {sess}: {e}"
            print(msg)
            logging.error(msg)
    await conn.close()
    logging.info("Finished sync_chats.py")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_file", type=str, help="Path to the session file")
    args = parser.parse_args()
    session_files = [args.session_file] if args.session_file else None
    session_files = sm.get_session_files(session_files)
    asyncio.run(main(session_files=session_files))
