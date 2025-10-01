#!/usr/bin/env python3
"""
Test script to check imports for the real-time chat list service
"""

try:
    print("Testing basic imports...")
    
    # Test telethon imports
    from telethon import TelegramClient, events
    print("✓ Telethon basic imports OK")
    
    # Test specific type imports
    from telethon.tl.types import User, Chat, Channel
    print("✓ Telethon types imports OK")
    
    # Test our module imports
    import telegram_sync.config as config
    print("✓ Config import OK")
    
    # Test the main service
    from telegram_sync.realtime_chat_list import chat_list_service
    print("✓ Real-time chat list service import OK")
    
    print("\n🎉 All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ General error: {e}")
    import traceback
    traceback.print_exc()