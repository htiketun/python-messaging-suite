#!/usr/bin/env python3
"""
Chat Data Retrieval Example

This script demonstrates how to get chat data using the new API endpoint
that mimics the Django TelegramChatDetailView functionality.
"""

import asyncio
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
SESSION_FILE = "session_916cfcaa.session"  # Replace with your session file

def print_response(response, title):
    """Print API response nicely"""
    print(f"\n=== {title} ===")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")
    print("=" * 60)

def test_get_chat_data():
    """Test the get chat data endpoint"""
    
    print("🔍 Testing Chat Data Retrieval")
    print(f"Base URL: {BASE_URL}")
    print(f"Session File: {SESSION_FILE}")
    
    # Example chat IDs - replace with actual chat IDs from your database
    test_chat_ids = [
        123456789,     # Example user chat
        -987654321,    # Example group chat (negative ID)
        # Add your actual chat IDs here
    ]
    
    for chat_id in test_chat_ids:
        print(f"\n{'='*60}")
        print(f"Testing Chat ID: {chat_id}")
        print('='*60)
        
        # 1. Get chat data with messages
        print(f"\n1. Getting chat data WITH messages for {chat_id}...")
        response = requests.get(
            f"{BASE_URL}/realtime/chat-data/{chat_id}",
            params={
                "session_file": SESSION_FILE,
                "include_messages": True,
                "message_limit": 10
            }
        )
        print_response(response, f"Chat Data WITH Messages - {chat_id}")
        
        # 2. Get chat data without messages
        print(f"\n2. Getting chat data WITHOUT messages for {chat_id}...")
        response = requests.get(
            f"{BASE_URL}/realtime/chat-data/{chat_id}",
            params={
                "session_file": SESSION_FILE,
                "include_messages": False
            }
        )
        print_response(response, f"Chat Data WITHOUT Messages - {chat_id}")
        
        # If we got a successful response, show formatted data
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                chat_info = data.get("data", {})
                print(f"\n📋 Formatted Chat Info:")
                print(f"   Name: {chat_info.get('name', 'N/A')}")
                print(f"   Type: {chat_info.get('type', 'N/A')}")
                print(f"   Username: {chat_info.get('username', 'N/A')}")
                print(f"   Unread Count: {chat_info.get('unread_count', 0)}")
                print(f"   Last Seen: {chat_info.get('last_seen', 'N/A')}")
                
                if chat_info.get('last_message'):
                    last_msg = chat_info['last_message']
                    print(f"   Last Message: {last_msg.get('text', 'No text')[:50]}...")
                    print(f"   Last Message Date: {last_msg.get('date', 'N/A')}")
                
                messages = chat_info.get('messages', [])
                print(f"   Recent Messages: {len(messages)} messages")
        
        print("\n" + "="*60)

async def test_realtime_service_integration():
    """Test integration with realtime chat list service"""
    
    print("\n🔄 Testing Realtime Service Integration")
    
    # First start monitoring
    print("1. Starting chat list monitoring...")
    response = requests.post(
        f"{BASE_URL}/realtime/start-chat-list-monitoring/",
        params={"session_file": SESSION_FILE}
    )
    print_response(response, "Start Monitoring")
    
    if response.status_code == 200:
        # Wait for initial sync
        print("2. Waiting 3 seconds for initial sync...")
        await asyncio.sleep(3)
        
        # Now test getting chat data
        print("3. Testing chat data retrieval after monitoring started...")
        test_get_chat_data()
        
        # Stop monitoring
        print("4. Stopping monitoring...")
        response = requests.post(
            f"{BASE_URL}/realtime/stop-chat-list-monitoring/",
            params={"session_file": SESSION_FILE}
        )
        print_response(response, "Stop Monitoring")

def show_usage_examples():
    """Show different usage examples"""
    
    usage_examples = f"""
    
    📚 USAGE EXAMPLES
    ==================
    
    1. Basic Chat Data Retrieval:
    -----------------------------
    GET {BASE_URL}/realtime/chat-data/123456789?session_file={SESSION_FILE}
    
    2. Chat Data WITHOUT Messages:
    -------------------------------
    GET {BASE_URL}/realtime/chat-data/123456789?session_file={SESSION_FILE}&include_messages=false
    
    3. Chat Data WITH Limited Messages:
    ------------------------------------
    GET {BASE_URL}/realtime/chat-data/123456789?session_file={SESSION_FILE}&include_messages=true&message_limit=20
    
    4. JavaScript/Vue.js Example:
    ------------------------------
    
    async function getChatData(chatId, includeMessages = true, messageLimit = 50) {{
        try {{
            const response = await fetch(
                `{BASE_URL}/realtime/chat-data/${{chatId}}?` + 
                `session_file={SESSION_FILE}&` +
                `include_messages=${{includeMessages}}&` +
                `message_limit=${{messageLimit}}`
            );
            
            const data = await response.json();
            
            if (data.status === 'success') {{
                console.log('Chat data:', data.data);
                
                // Access chat info
                const chat = data.data;
                console.log('Chat name:', chat.name);
                console.log('Unread count:', chat.unread_count);
                
                // Access last message
                if (chat.last_message) {{
                    console.log('Last message:', chat.last_message.text);
                    console.log('Last message date:', chat.last_message.date);
                }}
                
                // Access messages
                console.log('Recent messages:', chat.messages.length);
                chat.messages.forEach(msg => {{
                    console.log(`Message: ${{msg.text}} (Date: ${{msg.date}})`);
                }});
                
                return chat;
            }} else {{
                console.error('Error:', data.message);
                return null;
            }}
        }} catch (error) {{
            console.error('Fetch error:', error);
            return null;
        }}
    }}
    
    // Usage in Vue.js component
    export default {{
        data() {{
            return {{
                currentChat: null,
                loading: false
            }}
        }},
        methods: {{
            async loadChat(chatId) {{
                this.loading = true;
                try {{
                    this.currentChat = await getChatData(chatId, true, 50);
                }} finally {{
                    this.loading = false;
                }}
            }}
        }}
    }}
    
    5. Python Example:
    ------------------
    
    import requests
    
    def get_chat_data(chat_id, session_file, include_messages=True, message_limit=50):
        response = requests.get(
            f"{BASE_URL}/realtime/chat-data/{{chat_id}}",
            params={{
                "session_file": session_file,
                "include_messages": include_messages,
                "message_limit": message_limit
            }}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return data["data"]
        
        return None
    
    # Usage
    chat_data = get_chat_data(123456789, "{SESSION_FILE}")
    if chat_data:
        print(f"Chat: {{chat_data['name']}}")
        print(f"Unread: {{chat_data['unread_count']}}")
        if chat_data['last_message']:
            print(f"Last message: {{chat_data['last_message']['text']}}")
    
    """
    
    print(usage_examples)

if __name__ == "__main__":
    print("=" * 80)
    print("    CHAT DATA RETRIEVAL TEST & USAGE GUIDE")
    print("=" * 80)
    
    print("\n🔧 Before running this test:")
    print("1. Make sure FastAPI server is running:")
    print("   uvicorn telegram_sync.api_sync:app --host 0.0.0.0 --port 8000")
    print("2. Update SESSION_FILE variable with your actual session file")
    print("3. Update test_chat_ids with actual chat IDs from your database")
    print("4. Ensure your session file is authorized")
    
    choice = input("\nChoose an option:")
    print("1. Test basic chat data retrieval")
    print("2. Test with realtime service integration") 
    print("3. Show usage examples only")
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == "1":
        test_get_chat_data()
    elif choice == "2":
        asyncio.run(test_realtime_service_integration())
    elif choice == "3":
        show_usage_examples()
    else:
        print("Invalid choice!")
    
    show_usage_examples()
    print("=" * 80)