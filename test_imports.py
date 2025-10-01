#!/usr/bin/env python
"""
Quick test script to check if all imports work correctly
"""
import os
import sys
import django

# Add the project directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'python-messaging-suite.settings')
django.setup()

try:
    print("Testing imports...")
    
    # Test basic Django imports
    from django.conf import settings
    print("✓ Django settings imported")
    
    # Test model imports
    from api.models.telegram_account import TelegramAccount
    print("✓ TelegramAccount model imported")
    
    # Test telethon service
    from telegram_sync.telethon_service import TelethonService
    print("✓ TelethonService imported")
    
    # Test views
    from api.views.telegram_auth import StartLoginView
    print("✓ Telegram auth views imported")
    
    print("\n✅ All imports successful!")
    print(f"✓ Using AUTH_USER_MODEL: {settings.AUTH_USER_MODEL}")
    print(f"✓ Telegram API ID configured: {'Yes' if hasattr(settings, 'TELEGRAM_API_ID') else 'No'}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Other error: {e}")
    sys.exit(1)