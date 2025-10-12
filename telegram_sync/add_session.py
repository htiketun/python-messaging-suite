import argparse
import asyncio
import uuid
import os
import telegram_sync.session_manager as sm
import telegram_sync.config as config
import telegram_sync.db as db
from telethon import errors
from telethon.tl.types import PeerUser

os.makedirs(config.SESSION_FOLDER, exist_ok=True)

async def check_user_in_database(user_id, session_username=None):
    """Check if user exists in your database from previous syncs"""
    try:
        conn = await db.get_db()
        
        # Get all telegram accounts to search across all sessions
        accounts = await conn.fetch("SELECT id, name FROM telegram_accounts")
        
        found_users = []
        for account in accounts:
            # Check if user exists in chats for this account
            chat = await conn.fetchrow(
                "SELECT * FROM telegram_chats WHERE id = $1 AND telegram_account_id = $2",
                user_id, account['id']
            )
            
            if chat:
                found_users.append({
                    'account_name': account['name'],
                    'account_id': account['id'],
                    'chat': dict(chat)
                })
        
        if found_users:
            print(f"✅ Found user {user_id} in database:")
            for user in found_users:
                print(f"   Account: {user['account_name']} (ID: {user['account_id']})")
                print(f"   Name: {user['chat']['name']}")
                print(f"   Username: {user['chat'].get('username', 'N/A')}")
                print(f"   Last seen: {user['chat'].get('last_seen', 'N/A')}")
                print("-" * 40)
            return found_users
        else:
            print(f"❌ User {user_id} not found in database")
            return None
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None
    finally:
        if conn:
            await conn.close()

async def send_message_via_database_info(user_id, message_text, session_username=None):
    """Try to send message using database information"""
    try:
        # First check if user exists in database
        db_users = await check_user_in_database(user_id, session_username)
        if not db_users:
            print("User not found in database. Try syncing chats first with --sync-all")
            return False
        
        # Try to send message using the information we have
        return await send_message_to_user(user_id, message_text, session_username)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def search_user_by_phone(phone_number, session_username=None):
    """Search for user by phone number"""
    try:
        # Setup client connection
        if session_username:
            client = sm.new_session(session_username)
        else:
            session_files = [f for f in os.listdir(config.SESSION_FOLDER) if f.endswith('.session')]
            if not session_files:
                print("No session files found.")
                return None
            session_username = os.path.splitext(session_files[0])[0]
            client = sm.new_session(session_username)
        
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"Session {session_username} is not authorized")
            await client.disconnect()
            return None
        
        # Try to find user by phone
        try:
            # Add + if not present
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
                
            entity = await client.get_entity(phone_number)
            print(f"✅ Found user by phone: {getattr(entity, 'first_name', 'Unknown')} {getattr(entity, 'last_name', '') or ''}")
            print(f"Username: @{getattr(entity, 'username', 'no_username')}")
            print(f"User ID: {entity.id}")
            print(f"Phone: {phone_number}")
            return entity.id
        except Exception as e:
            print(f"❌ Could not find user by phone {phone_number}: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None
    finally:
        if 'client' in locals():
            await client.disconnect()

async def force_sync_specific_user(user_id, session_username=None):
    """Try to force sync a specific user by getting their full info"""
    try:
        # Setup client connection
        if session_username:
            client = sm.new_session(session_username)
        else:
            session_files = [f for f in os.listdir(config.SESSION_FOLDER) if f.endswith('.session')]
            if not session_files:
                print("No session files found.")
                return False
            session_username = os.path.splitext(session_files[0])[0]
            client = sm.new_session(session_username)
        
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"Session {session_username} is not authorized")
            await client.disconnect()
            return False
        
        print(f"🔍 Attempting to resolve and cache user {user_id}...")
        
        # Try different methods to get user entity
        entity = None
        
        # Method 1: Direct entity lookup with error handling
        try:
            from telethon.tl.functions.users import GetUsersRequest
            from telethon.tl.types import InputUser
            
            # Try with access_hash 0 (might work for some users)
            input_user = InputUser(user_id=user_id, access_hash=0)
            result = await client(GetUsersRequest([input_user]))
            if result:
                entity = result[0]
                print(f"✅ Resolved user: {getattr(entity, 'first_name', 'Unknown')}")
        except Exception as e1:
            print(f"⚠️ GetUsersRequest failed: {e1}")
        
        # Method 2: Try to find in all dialogs including groups/channels
        if not entity:
            print("🔍 Searching in all dialogs (including groups)...")
            try:
                async for dialog in client.iter_dialogs():
                    if hasattr(dialog.entity, 'participants_count'):  # It's a group/channel
                        try:
                            async for participant in client.iter_participants(dialog):
                                if participant.id == user_id:
                                    entity = participant
                                    print(f"✅ Found user in group '{dialog.title}': {getattr(entity, 'first_name', 'Unknown')}")
                                    break
                        except Exception as part_error:
                            continue  # Skip groups we can't access
                    elif hasattr(dialog.entity, 'id') and dialog.entity.id == user_id:
                        entity = dialog.entity
                        print(f"✅ Found user in direct conversations: {getattr(entity, 'first_name', 'Unknown')}")
                        break
                    
                    if entity:
                        break
            except Exception as e2:
                print(f"⚠️ Group search failed: {e2}")
        
        if entity:
            # Cache the entity for future use
            print("💾 Caching user entity...")
            try:
                # This helps Telethon remember the user for future requests
                await client.get_entity(entity.id)
                return True
            except Exception as cache_error:
                print(f"⚠️ Could not cache entity: {cache_error}")
                return False
        else:
            print(f"❌ Could not resolve user {user_id} through any method")
            return False
            
    except Exception as e:
        print(f"❌ Error in force sync: {e}")
        return False
    finally:
        if 'client' in locals():
            await client.disconnect()

async def send_message_to_user(user_id, message_text, session_username=None):
    """Send a message to a specific user ID using an active session"""
    try:
        # If no specific session provided, use the first available session
        if session_username:
            session_file = os.path.join(config.SESSION_FOLDER, f"{session_username}.session")
            if not os.path.exists(session_file):
                print(f"Session file {session_file} not found")
                return False
            client = sm.new_session(session_username)
        else:
            # Find first available session
            session_files = [
                f for f in os.listdir(config.SESSION_FOLDER)
                if f.endswith('.session')
            ]
            
            if not session_files:
                print("No session files found. Please create a session first.")
                return False
            
            # Use first session file
            session_file = session_files[0]
            session_username = os.path.splitext(session_file)[0]
            client = sm.new_session(session_username)
        
        # Connect to Telegram
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"Session {session_username} is not authorized")
            await client.disconnect()
            return False
        
        # Get current user info
        me = await client.get_me()
        print(f"Connected as: {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
        print(f"Your User ID: {me.id}")
        
        # Send message to the specified user ID
        try:
            # Try multiple methods to resolve the entity
            entity = None
            # Method 1: Try to get entity directly by user ID
            try:
                entity = await client.get_entity(user_id)
                print(f"✅ Found user: {getattr(entity, 'first_name', 'Unknown')} {getattr(entity, 'last_name', '') or ''}")
            except Exception as e1:
                print(f"⚠️ Method 1 failed: {e1}")
                
                # Method 2: Try to find in dialogs (conversations)
                try:
                    print("🔍 Searching in your conversations...")
                    async for dialog in client.iter_dialogs():
                        if hasattr(dialog.entity, 'id') and dialog.entity.id == user_id:
                            entity = dialog.entity
                            print(f"✅ Found user in conversations: {getattr(entity, 'first_name', 'Unknown')} {getattr(entity, 'last_name', '') or ''}")
                            break
                    
                    if not entity:
                        print(f"⚠️ User {user_id} not found in your conversations")
                        
                        # Method 3: Try with PeerUser but add to entity cache first
                        try:
                            print("🔍 Attempting to resolve user entity...")
                            # This might work if the user is in your contacts or you've interacted before
                            from telethon.tl.functions.users import GetUsersRequest
                            from telethon.tl.types import InputUser
                            
                            # Try to get user info
                            input_user = InputUser(user_id=user_id, access_hash=0)  # We don't have access_hash
                            users = await client(GetUsersRequest([input_user]))
                            if users:
                                entity = users[0]
                                print(f"✅ Resolved user: {getattr(entity, 'first_name', 'Unknown')} {getattr(entity, 'last_name', '') or ''}")
                        except Exception as e3:
                            print(f"⚠️ Method 3 failed: {e3}")
                            
                except Exception as e2:
                    print(f"⚠️ Method 2 failed: {e2}")
            
            if not entity:
                print(f"❌ Could not resolve user entity for ID {user_id}")
                print("💡 Possible solutions:")
                print("   1. Make sure you have interacted with this user before")
                print("   2. Add the user to your contacts")
                print("   3. Try finding them by username instead of user ID")
                print("   4. Start a conversation with them first through the Telegram app")
                print("   5. Use --force-sync to try resolving the user")
                print("   6. Use --check-db to see if user exists in your database")
                return False
            
            # Send the message using the resolved entity
            message = await client.send_message(entity, message_text)
            print(f"✅ Message sent successfully to user {user_id}")
            print(f"Message ID: {message.id}")
            print(f"Message: {message_text}")
            
            return True
            
        except errors.PeerIdInvalidError:
            print(f"❌ Error: User ID {user_id} is invalid or not accessible")
            print("This usually means:")
            print("- The user ID doesn't exist")
            print("- You haven't interacted with this user before")
            print("- The user has blocked you")
            print("- You need to start a conversation with them first")
            return False
            
        except errors.UserIsBlockedError:
            print(f"❌ Error: You are blocked by user {user_id}")
            return False
            
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
        
    finally:
        if 'client' in locals():
            await client.disconnect()

async def find_user_by_username(username, session_username=None):
    """Find a user by username and return their user ID"""
    try:
        # Setup client connection
        if session_username:
            client = sm.new_session(session_username)
        else:
            session_files = [
                f for f in os.listdir(config.SESSION_FOLDER)
                if f.endswith('.session')
            ]
            if not session_files:
                print("No session files found.")
                return None
            session_username = os.path.splitext(session_files[0])[0]
            client = sm.new_session(session_username)
        
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"Session {session_username} is not authorized")
            await client.disconnect()
            return None
        
        # Search for user by username
        try:
            entity = await client.get_entity(username)
            print(f"✅ Found user: {getattr(entity, 'first_name', 'Unknown')} {getattr(entity, 'last_name', '') or ''}")
            print(f"Username: @{getattr(entity, 'username', 'no_username')}")
            print(f"User ID: {entity.id}")
            return entity.id
        except Exception as e:
            print(f"❌ Could not find user @{username}: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None
    finally:
        if 'client' in locals():
            await client.disconnect()

async def list_recent_conversations(session_username=None, limit=20):
    """List recent conversations to help find user IDs"""
    try:
        # Setup client connection
        if session_username:
            client = sm.new_session(session_username)
        else:
            session_files = [
                f for f in os.listdir(config.SESSION_FOLDER)
                if f.endswith('.session')
            ]
            if not session_files:
                print("No session files found.")
                return
            session_username = os.path.splitext(session_files[0])[0]
            client = sm.new_session(session_username)
        
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"Session {session_username} is not authorized")
            await client.disconnect()
            return
        
        print("Recent conversations:")
        print("-" * 70)
        
        count = 0
        async for dialog in client.iter_dialogs():
            if count >= limit:
                break
                
            if dialog.is_user:  # Only show user conversations, not groups
                entity = dialog.entity
                name = f"{getattr(entity, 'first_name', 'Unknown')} {getattr(entity, 'last_name', '') or ''}".strip()
                username = getattr(entity, 'username', None)
                user_id = entity.id
                
                print(f"{count + 1}. {name}")
                if username:
                    print(f"   Username: @{username}")
                print(f"   User ID: {user_id}")
                if dialog.message:
                    last_msg = dialog.message.message[:50] + "..." if len(dialog.message.message) > 50 else dialog.message.message
                    print(f"   Last message: {last_msg}")
                print("-" * 50)
                count += 1
        
        if count == 0:
            print("No recent conversations found.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'client' in locals():
            await client.disconnect()

async def list_sessions():
    """List all available sessions with their user info"""
    session_files = [
        f for f in os.listdir(config.SESSION_FOLDER)
        if f.endswith('.session')
    ]
    
    if not session_files:
        print("No session files found.")
        return
    
    print("Available sessions:")
    print("-" * 50)
    
    for i, session_file in enumerate(session_files, 1):
        session_username = os.path.splitext(session_file)[0]
        try:
            client = sm.new_session(session_username)
            await client.connect()
            
            if await client.is_user_authorized():
                me = await client.get_me()
                print(f"{i}. {session_username}")
                print(f"   Name: {me.first_name} {me.last_name or ''}")
                print(f"   Username: @{me.username or 'no_username'}")
                print(f"   User ID: {me.id}")
                print(f"   Phone: {me.phone or 'N/A'}")
            else:
                print(f"{i}. {session_username} (NOT AUTHORIZED)")
                
            await client.disconnect()
            
        except Exception as e:
            print(f"{i}. {session_username} (ERROR: {e})")
        
        print("-" * 30)

async def main(sync_all=False, send_message=False, user_id=None, message_text=None, session_username=None, 
               list_sessions_flag=False, find_username=None, list_conversations=False, check_db=False,
               search_phone=None, force_sync_user=None):
    if list_sessions_flag:
        await list_sessions()
        return
    
    if check_db and user_id:
        await check_user_in_database(user_id, session_username)
        return
    
    if search_phone:
        user_id_found = await search_user_by_phone(search_phone, session_username)
        if user_id_found:
            print(f"\n💡 To send a message to this user, use:")
            print(f"python add_session.py --send-message --user-id {user_id_found} --message \"Your message here\"")
        return
    
    if force_sync_user:
        success = await force_sync_specific_user(force_sync_user, session_username)
        if success:
            print(f"\n💡 User {force_sync_user} synced! Now try sending the message:")
            print(f"python add_session.py --send-message --user-id {force_sync_user} --message \"Your message here\"")
        return
    
    if find_username:
        user_id_found = await find_user_by_username(find_username, session_username)
        if user_id_found:
            print(f"\n💡 To send a message to this user, use:")
            print(f"python add_session.py --send-message --user-id {user_id_found} --message \"Your message here\"")
        return
    
    if list_conversations:
        await list_recent_conversations(session_username)
        return
    
    if send_message:
        if not user_id or not message_text:
            print("❌ Error: Both --user-id and --message are required for sending messages")
            return
        
        success = await send_message_to_user(user_id, message_text, session_username)
        if success:
            print("✅ Message sent successfully!")
        else:
            print("❌ Failed to send message")
        return
    
    if sync_all:
        print("Creating a Telegram session from session folder...")
        session_files = [
            os.path.join(config.SESSION_FOLDER, f)
            for f in os.listdir(config.SESSION_FOLDER)
            if f.endswith('.session')
        ]

        for session_file in session_files:
            print(f"Syncing all chats and messages for session file: {session_file}")
            username = os.path.splitext(os.path.basename(session_file))[0]
            client = sm.new_session(username)
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    await client.disconnect()
                    os.remove(session_file)
                    print(f"Skipping {username}: session is not authorized or requires login.")
                    continue
                conn = await db.get_db()
                me = await client.get_me()
                await db.upsert_telegram_account(conn, os.path.basename(client.session.filename), me)
                print(f"Finished syncing for session file: {session_file}")
            except Exception as e:
                print(f"Skipping {username}: encountered an error: {e}")
                continue
        return
    else:
        print("Creating a new Telegram session...")
        username = f"session_{uuid.uuid4().hex[:8]}"
        print(f"Generated unique session username: {username}")
        client = sm.new_session(username)
        await client.start()
        conn = await db.get_db()
        me = await client.get_me()
        await db.upsert_telegram_account(conn, os.path.basename(client.session.filename), me)
        print(f"Session for {username} created.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync-all", action="store_true", help="Sync all chats and messages for all session files after creating session")
    parser.add_argument("--send-message", action="store_true", help="Send a message to a specific user")
    parser.add_argument("--user-id", type=int, help="Target user ID to send message to")
    parser.add_argument("--message", type=str, help="Message text to send")
    parser.add_argument("--session", type=str, help="Specific session username to use (optional)")
    parser.add_argument("--list-sessions", action="store_true", help="List all available sessions")
    parser.add_argument("--find-username", type=str, help="Find user ID by username (e.g., --find-username john_doe)")
    parser.add_argument("--list-conversations", action="store_true", help="List recent conversations with user IDs")
    parser.add_argument("--check-db", action="store_true", help="Check if user exists in database (requires --user-id)")
    parser.add_argument("--search-phone", type=str, help="Search for user by phone number")
    parser.add_argument("--force-sync", type=int, help="Force sync a specific user ID")
    
    args = parser.parse_args()
    
    asyncio.run(main(
        sync_all=args.sync_all,
        send_message=args.send_message,
        user_id=args.user_id,
        message_text=args.message,
        session_username=args.session,
        list_sessions_flag=args.list_sessions,
        find_username=args.find_username,
        list_conversations=args.list_conversations,
        check_db=args.check_db,
        search_phone=args.search_phone,
        force_sync_user=args.force_sync
    ))