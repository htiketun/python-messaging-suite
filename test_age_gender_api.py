#!/usr/bin/env python3
"""
Age and Gender Prediction API Test

This script demonstrates how to use the new age and gender prediction APIs.
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
    print("=" * 70)

def test_age_gender_api():
    """Test the age and gender prediction APIs"""
    
    print("👤 Testing Age and Gender Prediction APIs")
    print(f"Base URL: {BASE_URL}")
    print(f"Session File: {SESSION_FILE}")
    
    # Example chat IDs - replace with actual user chat IDs from your database
    test_chat_ids = [
        123456789,     # Example user chat 1
        987654321,     # Example user chat 2
        # Add your actual user chat IDs here
    ]
    
    print("\n🔧 Step 1: Starting chat list monitoring (required for age/gender APIs)...")
    response = requests.post(
        f"{BASE_URL}/realtime/start-chat-list-monitoring/",
        params={"session_file": SESSION_FILE}
    )
    print_response(response, "Start Monitoring")
    
    if response.status_code != 200 or response.json().get("status") != "success":
        print("❌ Failed to start monitoring. Cannot test age/gender APIs.")
        return
    
    print("✅ Monitoring started successfully!")
    print("⏳ Waiting 3 seconds for initialization...")
    import time
    time.sleep(3)
    
    # Test individual chat age/gender prediction
    for chat_id in test_chat_ids:
        print(f"\n{'='*70}")
        print(f"Testing Chat ID: {chat_id}")
        print('='*70)
        
        print(f"\n1. Getting age/gender for chat {chat_id}...")
        response = requests.get(
            f"{BASE_URL}/realtime/age-gender/{chat_id}",
            params={"session_file": SESSION_FILE}
        )
        print_response(response, f"Age/Gender for Chat {chat_id}")
        
        # Show formatted results
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print(f"\n📊 Results:")
                print(f"   Chat ID: {data.get('chat_id')}")
                print(f"   Gender: {data.get('gender', 'Unknown')}")
                print(f"   Age: {data.get('age', 'Unknown')}")
                print(f"   Source: {data.get('source', 'Unknown')}")
                
                if data.get('prediction_data'):
                    pred_data = data['prediction_data']
                    print(f"   Prediction based on:")
                    print(f"     - Name: {pred_data.get('name', 'N/A')}")
                    print(f"     - Bio: {pred_data.get('bio', 'N/A')[:100]}...")
                    print(f"     - DOB: {pred_data.get('dob', 'N/A')}")
    
    # Test bulk prediction
    print(f"\n{'='*70}")
    print("BULK PREDICTION TEST")
    print('='*70)
    
    print("\n2. Running bulk age/gender prediction for all private chats...")
    response = requests.post(
        f"{BASE_URL}/realtime/bulk-predict-age-gender/",
        params={
            "session_file": SESSION_FILE,
            "force_update": False  # Only predict for chats without age/gender
        }
    )
    print_response(response, "Bulk Age/Gender Prediction")
    
    # Show bulk results summary
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "success":
            print(f"\n📈 Bulk Prediction Summary:")
            print(f"   Total Chats: {data.get('total_chats', 0)}")
            print(f"   Processed: {data.get('processed', 0)}")
            print(f"   Updated: {data.get('updated', 0)}")
            print(f"   Errors: {data.get('errors', 0)}")
            
            # Show first few details
            details = data.get('details', [])
            if details:
                print(f"\n📋 First 5 Results:")
                for i, detail in enumerate(details[:5]):
                    chat_display = detail.get('chat_name', f"Chat {detail.get('chat_id')}")
                    if detail.get('status') == 'success':
                        print(f"   {i+1}. {chat_display}: {detail.get('gender', 'N/A')}, {detail.get('age', 'N/A')} ({detail.get('source', 'N/A')})")
                    else:
                        print(f"   {i+1}. {chat_display}: ERROR - {detail.get('error', 'Unknown')}")
    
    # Test force update
    print(f"\n{'='*70}")
    print("FORCE UPDATE TEST")
    print('='*70)
    
    choice = input("\nDo you want to test force update (re-predict all chats)? (y/n): ").lower().strip()
    if choice == 'y':
        print("\n3. Running bulk prediction with force update...")
        response = requests.post(
            f"{BASE_URL}/realtime/bulk-predict-age-gender/",
            params={
                "session_file": SESSION_FILE,
                "force_update": True  # Re-predict all chats
            }
        )
        print_response(response, "Bulk Age/Gender Prediction (Force Update)")
    
    # Stop monitoring
    print(f"\n{'='*70}")
    print("CLEANUP")
    print('='*70)
    
    print("\n4. Stopping monitoring...")
    response = requests.post(
        f"{BASE_URL}/realtime/stop-chat-list-monitoring/",
        params={"session_file": SESSION_FILE}
    )
    print_response(response, "Stop Monitoring")

def show_usage_examples():
    """Show different usage examples"""
    
    usage_examples = f"""
    
    📚 AGE & GENDER API USAGE EXAMPLES
    ===================================
    
    1. Get Age/Gender for Single Chat:
    -----------------------------------
    GET {BASE_URL}/realtime/age-gender/123456789?session_file={SESSION_FILE}
    
    Response:
    {{
        "status": "success",
        "chat_id": 123456789,
        "gender": "male",
        "age": "25-35",
        "source": "predicted",
        "prediction_data": {{
            "name": "John Doe",
            "bio": "Software developer...",
            "dob": "1990-01-15"
        }}
    }}
    
    2. Bulk Predict for All Private Chats:
    ---------------------------------------
    POST {BASE_URL}/realtime/bulk-predict-age-gender/?session_file={SESSION_FILE}&force_update=false
    
    Response:
    {{
        "status": "success",
        "session_file": "{SESSION_FILE}",
        "total_chats": 50,
        "processed": 50,
        "updated": 25,
        "errors": 0,
        "details": [...]
    }}
    
    3. Force Update All Chats:
    ---------------------------
    POST {BASE_URL}/realtime/bulk-predict-age-gender/?session_file={SESSION_FILE}&force_update=true
    
    4. JavaScript/Vue.js Example:
    ------------------------------
    
    async function getAgeGender(chatId) {{
        try {{
            const response = await fetch(
                `{BASE_URL}/realtime/age-gender/${{chatId}}?session_file={SESSION_FILE}`
            );
            const data = await response.json();
            
            if (data.status === 'success') {{
                console.log('Age/Gender data:', {{
                    chatId: data.chat_id,
                    gender: data.gender,
                    age: data.age,
                    source: data.source
                }});
                return data;
            }} else {{
                console.error('Error:', data.message);
                return null;
            }}
        }} catch (error) {{
            console.error('Fetch error:', error);
            return null;
        }}
    }}
    
    async function bulkPredictAgeGender(forceUpdate = false) {{
        try {{
            const response = await fetch(
                `{BASE_URL}/realtime/bulk-predict-age-gender/?` +
                `session_file={SESSION_FILE}&force_update=${{forceUpdate}}`,
                {{ method: 'POST' }}
            );
            const data = await response.json();
            
            if (data.status === 'success') {{
                console.log('Bulk prediction results:', {{
                    totalChats: data.total_chats,
                    processed: data.processed,
                    updated: data.updated,
                    errors: data.errors
                }});
                return data;
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
                chatAgeGenderData: {{}},
                bulkPredictionStatus: null
            }}
        }},
        methods: {{
            async loadChatAgeGender(chatId) {{
                const data = await getAgeGender(chatId);
                if (data) {{
                    this.chatAgeGenderData[chatId] = data;
                }}
            }},
            
            async runBulkPrediction(forceUpdate = false) {{
                this.bulkPredictionStatus = 'running';
                const result = await bulkPredictAgeGender(forceUpdate);
                this.bulkPredictionStatus = result ? 'completed' : 'error';
                return result;
            }}
        }}
    }}
    
    5. Python Example:
    ------------------
    
    import requests
    
    def get_age_gender(chat_id, session_file):
        response = requests.get(
            f"{BASE_URL}/realtime/age-gender/{{chat_id}}",
            params={{"session_file": session_file}}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return {{
                    'chat_id': data['chat_id'],
                    'gender': data['gender'],
                    'age': data['age'],
                    'source': data['source']
                }}
        return None
    
    def bulk_predict_age_gender(session_file, force_update=False):
        response = requests.post(
            f"{BASE_URL}/realtime/bulk-predict-age-gender/",
            params={{
                "session_file": session_file,
                "force_update": force_update
            }}
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    
    # Usage
    age_gender = get_age_gender(123456789, "{SESSION_FILE}")
    if age_gender:
        print(f"Chat {{age_gender['chat_id']}}: {{age_gender['gender']}}, {{age_gender['age']}}")
    
    bulk_result = bulk_predict_age_gender("{SESSION_FILE}")
    if bulk_result:
        print(f"Processed {{bulk_result['processed']}} chats, updated {{bulk_result['updated']}}")
    
    6. Prerequisites:
    -----------------
    • FastAPI server must be running
    • Session must be started with /realtime/start-chat-list-monitoring/
    • Only works with private chats (user-to-user conversations)
    • Requires OpenAI API key configured in the service
    • Database must have telegram_chats table with gender/age columns
    
    """
    
    print(usage_examples)

if __name__ == "__main__":
    print("=" * 80)
    print("    AGE & GENDER PREDICTION API TEST & USAGE GUIDE")
    print("=" * 80)
    
    print("\n🔧 Before running this test:")
    print("1. Make sure FastAPI server is running:")
    print("   uvicorn telegram_sync.api_sync:app --host 0.0.0.0 --port 8000")
    print("2. Update SESSION_FILE variable with your actual session file")
    print("3. Update test_chat_ids with actual USER chat IDs (not groups)")
    print("4. Ensure your session file is authorized")
    print("5. Make sure OpenAI API key is configured in realtime_chat_list.py")
    
    choice = input("\nChoose an option:")
    print("1. Test age/gender prediction APIs")
    print("2. Show usage examples only")
    choice = input("Enter choice (1/2): ").strip()
    
    if choice == "1":
        test_age_gender_api()
    elif choice == "2":
        show_usage_examples()
    else:
        print("Invalid choice!")
    
    show_usage_examples()
    print("=" * 80)