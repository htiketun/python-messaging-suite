#!/usr/bin/env python3
"""
Real-time Chat List Service Usage Example

This script demonstrates how to use the real-time chat list service
for monitoring Telegram chats and storing data in the database.
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
    print("=" * 50)

async def test_chat_list_service():
    """Test the real-time chat list service"""
    
    print("🚀 Testing Real-time Chat List Service")
    print(f"Base URL: {BASE_URL}")
    print(f"Session File: {SESSION_FILE}")
    
    # 1. Check current status
    print("\n1. Checking current monitoring status...")
    response = requests.get(f"{BASE_URL}/realtime/chat-list-status/")
    print_response(response, "Current Status")
    
    # 2. Start monitoring
    print("\n2. Starting chat list monitoring...")
    response = requests.post(f"{BASE_URL}/realtime/start-chat-list-monitoring/", 
                           params={"session_file": SESSION_FILE})
    print_response(response, "Start Monitoring")
    
    if response.status_code == 200 and response.json().get("status") == "success":
        print("✅ Monitoring started successfully!")
        
        # Wait a bit for initial sync
        print("\n3. Waiting 5 seconds for initial sync...")
        await asyncio.sleep(5)
        
        # 4. Check status again
        print("\n4. Checking status after start...")
        response = requests.get(f"{BASE_URL}/realtime/chat-list-status/")
        print_response(response, "Status After Start")
        
        # 5. Manual database sync
        print("\n5. Performing manual database sync...")
        response = requests.post(f"{BASE_URL}/realtime/sync-database/", 
                               params={"session_file": SESSION_FILE})
        print_response(response, "Manual Database Sync")
        
        # 6. Stop monitoring
        print("\n6. Stopping monitoring...")
        response = requests.post(f"{BASE_URL}/realtime/stop-chat-list-monitoring/", 
                               params={"session_file": SESSION_FILE})
        print_response(response, "Stop Monitoring")
        
    else:
        print("❌ Failed to start monitoring")
        
    print("\n🎉 Test completed!")

def test_websocket_connection():
    """Test WebSocket connection with JavaScript-like example"""
    
    websocket_example = """
    // WebSocket Connection Example (JavaScript)
    const socket = new WebSocket('ws://localhost:8000/ws/chat-list');
    
    socket.onopen = () => {
        console.log('✅ Connected to chat list WebSocket');
        
        // Request current chat list
        socket.send(JSON.stringify({
            type: 'get_chat_list',
            session_file: '""" + SESSION_FILE + """'
        }));
        
        // Send heartbeat
        setInterval(() => {
            socket.send(JSON.stringify({type: 'ping'}));
        }, 30000);
    };
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('📨 Received:', data.type);
        
        switch(data.type) {
            case 'connection_established':
                console.log('🔗 Connection established');
                break;
                
            case 'chat_list_initial':
                console.log('📋 Initial chat list:', data.chats.length, 'chats');
                updateChatList(data.chats);
                break;
                
            case 'chat_list_update':
                console.log('🔄 Chat update for:', data.chat_id);
                updateSingleChat(data);
                break;
                
            case 'user_status_update':
                console.log('👤 User status update:', data.user_id);
                updateUserStatus(data);
                break;
                
            case 'pong':
                console.log('🏓 Heartbeat response');
                break;
        }
    };
    
    socket.onclose = () => {
        console.log('❌ WebSocket disconnected');
        // Auto-reconnect after 3 seconds
        setTimeout(() => {
            console.log('🔄 Reconnecting...');
            // Reinitialize connection
        }, 3000);
    };
    
    socket.onerror = (error) => {
        console.error('💥 WebSocket error:', error);
    };
    
    function updateChatList(chats) {
        // Update your Vue.js chat list
        this.users = chats.map(chat => ({
            id: chat.id,
            name: chat.name,
            type: chat.type,
            unread_count: chat.unread_count,
            is_online: chat.online_status?.type === 'online',
            last_message: chat.last_message,
            // ... other properties
        }));
    }
    
    function updateSingleChat(data) {
        // Update single chat in the list
        const chatIndex = this.users.findIndex(user => user.id === data.chat_id);
        if (chatIndex !== -1) {
            this.users[chatIndex].last_message = data.last_message;
            // Move to top of list
            const chat = this.users.splice(chatIndex, 1)[0];
            this.users.unshift(chat);
        }
    }
    
    function updateUserStatus(data) {
        // Update user online status
        const userIndex = this.users.findIndex(user => user.id === data.user_id);
        if (userIndex !== -1) {
            this.users[userIndex].online_status = data.status;
            this.users[userIndex].is_online = data.status?.type === 'online';
        }
    }
    """
    
    print("\n🌐 WebSocket Connection Example:")
    print(websocket_example)

if __name__ == "__main__":
    print("=" * 60)
    print("    REAL-TIME CHAT LIST SERVICE USAGE GUIDE")
    print("=" * 60)
    
    print("\n📋 Available API Endpoints:")
    print("• POST /realtime/start-chat-list-monitoring/?session_file=<file>")
    print("• POST /realtime/stop-chat-list-monitoring/?session_file=<file>")
    print("• GET  /realtime/chat-list-status/")
    print("• POST /realtime/sync-database/?session_file=<file>")
    print("• WS   /ws/chat-list")
    
    print("\n🔧 Before running this test:")
    print("1. Make sure FastAPI server is running:")
    print("   uvicorn telegram_sync.api_sync:app --host 0.0.0.0 --port 8000")
    print("2. Update SESSION_FILE variable with your actual session file")
    print("3. Ensure your session file is authorized")
    
    choice = input("\nDo you want to run the API test? (y/n): ").lower().strip()
    
    if choice == 'y':
        asyncio.run(test_chat_list_service())
    
    print("\n" + "=" * 60)
    test_websocket_connection()
    print("=" * 60)