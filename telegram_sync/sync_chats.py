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
            # msg = f"Session file {session_file} exists but Telegram session is unauthorized. Skipping."
            # print(msg)
            # logging.warning(msg)
            return
        import base64
        me = await client.get_me()
        counts = 0
        me_name = getattr(me, 'first_name', 'Me')
        me_photo_filename = f"telegram_photo/{me.id}/{me_name}_photo.jpg"
        me_base64_str = None
        if os.path.exists(me_photo_filename):
            with open(me_photo_filename, "rb") as image_file:
                me_base64_str = base64.b64encode(image_file.read()).decode("utf-8")
        else:
            me_photo_path = await client.download_profile_photo(me, file=me_photo_filename)
            if me_photo_path and os.path.exists(me_photo_path):
                with open(me_photo_path, "rb") as image_file:
                    me_base64_str = base64.b64encode(image_file.read()).decode("utf-8")
                # Do not remove the photo file, keep for future use


        telegram_account_id = await db.get_telegram_account_id(conn, session_file)
        if not telegram_account_id:
            await db.upsert_telegram_account(conn, session_file, me, counts, me_base64_str)
            telegram_account_id = await db.get_telegram_account_id(conn, session_file)

        if not telegram_account_id:
            # msg = f"Failed to get or create telegram_account_id for session {session_file}. Skipping."
            # print(msg)
            # logging.error(msg)
            await client.disconnect()
            return

        full = await client(GetFullUserRequest(me.username)) if me.username else None
        # Save the full user info as JSON for inspection
        session_dir = os.path.dirname(session_file)
        full_json_path = os.path.join(session_dir, os.path.basename(session_file) + ".full.json")
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
            if dialog.is_user:
                #logg message detail
                if dialog.unread_count > 0:
                    counts += dialog.unread_count
                entity = dialog.entity
                name = getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown'))
                photo_filename = f"telegram_photo/{me.id}/{entity.id}_photo.jpg"
                base64_str = None

                if os.path.exists(photo_filename):
                    # Use existing photo
                    with open(photo_filename, "rb") as image_file:
                        base64_str = base64.b64encode(image_file.read()).decode("utf-8")
                else:
                    # Download profile photo only once
                    photo_path = await client.download_profile_photo(entity, file=photo_filename)
                    if photo_path and os.path.exists(photo_path):
                        with open(photo_path, "rb") as image_file:
                            base64_str = base64.b64encode(image_file.read()).decode("utf-8")
                        # Optionally, keep the file for future use (do not remove)
                        # os.remove(photo_path)  # Remove only if you don't want to keep

                await db.upsert_chat(conn, telegram_account_id, dialog, base64_str)
                await db.upsert_message(conn, telegram_account_id, dialog.id, dialog.message)


        await db.upsert_telegram_account(conn, session_file, me, counts, me_base64_str)

        await asyncio.sleep(2)
        await client.disconnect()

    except errors.UnauthorizedError:
        try:
            await client.disconnect()
        except Exception:
            pass
        os.remove(session_file)
        # msg = f"Session file {session_file} exists but Telegram session is unauthorized. Skipping."
        # print(msg)
        # logging.warning(msg)
    except Exception as e:
        # want to get error line number
        # msg = f"Error with session {session_file}: {e}"
        # print(msg)
        logging.error(msg)

async def main(session_files=None):
    # logging.info("Started sync_chats.py")
    if session_files is None:
        session_files = sm.get_session_files()
    if not session_files:
        # msg = "No session files found. Use add_session.py first."
        # print(msg)
        # logging.warning(msg)
        return

    conn = await db.get_db()
    for sess in session_files:
        try:
            await fetch_and_sync(sess, conn)
        except errors.FloodWaitError as e:
            # msg = f"FloodWait: Sleeping for {e.seconds} seconds..."
            # print(msg)
            # logging.warning(msg)
            await asyncio.sleep(e.seconds)
        except Exception as e:
            msg = f"Error with session {sess}: {e}"
            # print(msg)
            logging.error(msg)
    await conn.close()
    # logging.info("Finished sync_chats.py")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_file", type=str, help="Path to the session file")
    args = parser.parse_args()
    session_files = [args.session_file] if args.session_file else None
    session_files = sm.get_session_files(session_files)
    asyncio.run(main(session_files=session_files))
