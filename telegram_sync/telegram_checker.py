import re
from telegram_sync import config
from telethon.sync import TelegramClient
from telethon.errors import UsernameNotOccupiedError
from telethon.tl.functions.users import GetFullUserRequest
from transformers import pipeline
import json

api_id = config.TELEGRAM_API_ID
api_hash = config.TELEGRAM_API_HASH

def extract_gender_and_dob(bio):
    gender = None
    dob = None
    if bio:
        bio_lower = bio.lower()
        if "male" in bio_lower:
            gender = "Male"
        elif "female" in bio_lower:
            gender = "Female"
        dob_match = re.search(r'\b(\d{1,4}[./-]\d{1,2}[./-]\d{1,4})\b', bio)
        if dob_match:
            dob = dob_match.group(1)
    return gender, dob


# AI gender detection
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
def ask_ai_gender(first_name, last_name, bio=""):
    """
    Uses a zero-shot classification model to predict gender based on name and bio.
    Returns "male", "female", or "unknown".
    """
    text = (
        f"{first_name} {last_name} "
        f"{bio} "
        "Is this name is male or female?"
    )
    print(f"AI classification input: {text}")
    candidate_labels = ["female", "male"]
    try:
        result = classifier(text, candidate_labels)
        result = {k: v for k, v in zip(result['labels'], result['scores'])}
        print(f"AI classification raw result: {result}")
        if result.get("male", 0) > 0.6:
            return "male"
        else:
            return "female"
    except Exception as e:
        print(f"AI gender detection error: {e}")
        exit()
        return "unknown"

def check_telegram_users(usernames):
    male_count = 0
    female_count = 0
    with TelegramClient('anon', api_id, api_hash) as client:
        for username in usernames:
            try:
                user = client.get_entity(username)
            except UsernameNotOccupiedError:
                print(f"Username @{username} does not exist.")
                continue
            except Exception as e:
                print(f"Error fetching user @{username}: {e}")
                continue
          
            bio = getattr(user, "about", None)
            gender, _ = extract_gender_and_dob(bio or "")
            if not gender:
                first_name = getattr(user, "first_name", "")
                last_name = getattr(user, "last_name", "")
                ai_gender = ask_ai_gender(first_name, last_name, bio or "")
                if ai_gender == "male":
                    gender = "Male"
                elif ai_gender == "female":
                    gender = "Female"
                else:
                    gender = None ; 
            if gender == "Male":
                male_count += 1
            elif gender == "Female":
                female_count += 1

    print(f"Total Male: {male_count}")
    print(f"Total Female: {female_count}")
    if male_count > female_count:
        print("Mostly Male")
    elif female_count > male_count:
        print("Mostly Female")
    else:
        print("Equal number of Males and Females or not enough data.")

if __name__ == "__main__":
    usernames = input("Enter Telegram usernames separated by commas (without @): ").split(",")
    usernames = [u.strip() for u in usernames if u.strip()]
    check_telegram_users(usernames)
