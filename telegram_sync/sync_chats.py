import asyncio
import json
import os
import logging
import re
from telethon import TelegramClient, errors
import telegram_sync.config as config
import telegram_sync.session_manager as sm
import telegram_sync.db as db
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import UserStatusEmpty, UserStatusOnline, UserStatusOffline, UserStatusRecently, UserStatusLastWeek, UserStatusLastMonth

# Setup logging
logging.basicConfig(
    filename='chats.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)


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
        "sex": "",
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

from openai import OpenAI
import random
client = OpenAI(api_key="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")

client = OpenAI(api_key="1")
def predict_gender_age(name, bio, dob):
    if dob:
        prompt = (
            f"Given the following information:\n"
            f"Name: {name}\n"
            f"Bio: {bio}\n"
            f"Date of Birth: {dob}\n"
            "Predict the most likely gender (male or female) and the exact age (not a range) based on the date of birth. "
            "Respond ONLY with a valid JSON object like this: {\"gender\": \"male\", \"age\": \"32\"} and nothing else. "
            "If you are unsure, make your best guess."
        )
    else:
        prompt = (
            f"Given the following information:\n"
            f"Name: {name}\n"
            f"Bio: {bio}\n"
            f"Date of Birth: {dob}\n"
            "Predict the most likely gender (male or female) and an age range e.g. '18-25', '25-35', '35-45', '45-55', '55-65', '65+'. "
            "Respond ONLY with a valid JSON object like this: {\"gender\": \"male\", \"age\": \"20-30\"} and nothing else. "
            "If you are unsure, make your best guess."
        )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that predicts gender (male or female) and age range (like '20-30', '30-40', etc) from name, bio, and date of birth. Respond ONLY with a valid JSON object like {\"gender\": \"male\", \"age\": \"20-30\"} and nothing else. Never leave gender or age empty. If unsure, make your best guess."},
            {"role": "user", "content": prompt}
        ]
    )

    result = response.choices[0].message.content.strip()
    match = re.search(r'\{.*\}', result)
    if match:
        return match.group(0)
    else:
        genders = ["male", "female"]
        start_age = random.randint(18, 60)
        end_age = start_age + random.choice([3, 5, 8, 10])
        age_range = f"{start_age}-{end_age}"
        return json.dumps({
            "gender": random.choice(genders),
            "age": age_range
        })

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
        import base64
        me = await client.get_me()
        counts = 0
        me_name = getattr(me, 'username ', 'Me')

        me_photo_filename = f"media/telegram_photo/{me.id}/{me_name}_photo.jpg"
        full_photo_url = None
        if os.path.exists(me_photo_filename):
            full_photo_url = f"{me_photo_filename}"
        else:
            me_photo_path = await client.download_profile_photo(me, file=me_photo_filename)
            if me_photo_path and os.path.exists(me_photo_path):
                full_photo_url = f"{me_photo_filename}"

        telegram_account_id = await db.get_telegram_account_id(conn, session_file)
        if not telegram_account_id:
            await db.upsert_telegram_account(conn, session_file, me, counts, full_photo_url)
            telegram_account_id = await db.get_telegram_account_id(conn, session_file)
        if not telegram_account_id:
            await client.disconnect()
            return

        full = await client(GetFullUserRequest(me.id)) if me.id else None
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

        msg = f"Syncing chats for: {me.id or me.phone}"
        print(msg)

        async for dialog in client.iter_dialogs():
            #logg message detail
            # if dialog.is_user:
                
                if dialog.unread_count > 0:
                    counts += dialog.unread_count
                entity = dialog.entity
                first_name = getattr(entity, "first_name", "") or ""
                last_name = getattr(entity, "last_name", "") or ""
                name = (first_name + " " + last_name).strip() or (entity.username or "Unknown")
                dob = ""  # Date of birth is not available in Telegram User object
                bio = ""
                try:
                    # Try to get bio if available (requires GetFullUserRequest)
                    if hasattr(entity, "id") and entity.id:
                        full_user = await client(GetFullUserRequest(entity.id))
                        # Try to extract date of birth (dob) if available
                        dob = ""
                        if hasattr(full_user.full_user, "birthday") and full_user.full_user.birthday:
                            # birthday is a Birthday object with day, month, year
                            b = full_user.full_user.birthday
                            dob = f"{b.year:04d}-{b.month:02d}-{b.day:02d}"
                            bio = hasattr(full_user.full_user, "about") and full_user.full_user.about or ""
                except Exception as e:
                    logging.warning(f"Could not fetch full user info for {entity.id}: {e}")

                alreadySet = await db.check_age_and_gender_already_set(conn, dialog.id)
                
                gender = ""
                age = ""
                if not alreadySet:
                    prediction = predict_gender_age(name, dob, bio)
                    print(f"Prediction for {name} ({dialog.id}): {prediction}")
                    try:
                        pred_json = json.loads(prediction)
                        gender = pred_json.get("gender")
                        age = pred_json.get("age")
                    except json.JSONDecodeError:
                        logging.warning(f"Could not decode JSON for prediction: {prediction}")
                else:
                    getAlreadySet = await db.get_age_and_gender_already_set(conn, dialog.id)
                    gender = getAlreadySet.get("gender")
                    age = getAlreadySet.get("age")

                photo_filename = f"media/telegram_photo/{me.id}/{entity.id}_photo.jpg"
                base64_str = None
                full_photo_url_chat = None

                if os.path.exists(photo_filename):
                    # Use existing photo
                    full_photo_url_chat = f"{photo_filename}"
                    # with open(photo_filename, "rb") as image_file:
                    #     base64_str = base64.b64encode(image_file.read()).decode("utf-8")
                else:
                    # Download profile photo only once
                    photo_path = await client.download_profile_photo(entity, file=photo_filename)
                    if photo_path and os.path.exists(photo_path):
                        full_photo_url_chat = f"{photo_filename}"
                        # with open(photo_path, "rb") as image_file:
                        #     base64_str = base64.b64encode(image_file.read()).decode("utf-8")
                        # Optionally, keep the file for future use (do not remove)
                        # os.remove(photo_path)  # Remove only if you don't want to keep
                
                # i want to get last seen online status
                last_seen = None
          
                # Extract last seen/online status from entity.status if available
                if hasattr(entity, "status") and entity.status:
                    status = entity.status
                    last_seen = get_user_status(status)

                await db.upsert_chat(conn, telegram_account_id, dialog, full_photo_url=full_photo_url_chat, gender=gender, age=age, last_seen=last_seen)
                await db.upsert_message(conn, telegram_account_id, dialog.id, dialog.message)

        await db.upsert_telegram_account(conn, session_file, me, counts, full_photo_url=full_photo_url)

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
        msg = f"Error with session {session_file}: {e}"
        print(msg)
        logging.error(msg)

from datetime import datetime, timedelta, timezone

def get_user_status(status):
    if isinstance(status, UserStatusEmpty):
        return None
    elif isinstance(status, UserStatusOnline):
        return datetime.now(timezone.utc).isoformat()
    elif isinstance(status, UserStatusOffline):
        return status.was_online.isoformat()
    elif isinstance(status, UserStatusRecently):
        # Approximate "recently" as 5 minutes ago
        return (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    elif isinstance(status, UserStatusLastWeek):
        # Approximate "last week" as 3 days ago
        return (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    elif isinstance(status, UserStatusLastMonth):
        # Approximate "last month" as 15 days ago
        return (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    else:
        return None
    
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
