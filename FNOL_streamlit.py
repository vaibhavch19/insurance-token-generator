import streamlit as st
import requests
from datetime import datetime

# App setup
st.set_page_config(page_title="FNOL Chatbot", page_icon="🆘")
st.title("🆘 FNOL Claims Assistant")

# Backend configuration
BACKEND_API = "http://localhost:8000"

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hello! I'm here to help with your insurance claim. Could you please share what happened?"
    }]

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def process_message(user_input: str):
    """Send message to backend and handle response"""
    print("📤 process_message called with:", user_input)
    try:
        # Debug print to console
        print("\n=== Sending to backend ===")
        print(f"URL: {BACKEND_API}/api/chat")
        print("Payload:", {
            'message': user_input,
            'thread_id': st.session_state.thread_id
        })

        response = requests.post(
            f"{BACKEND_API}/api/chat",
            json={
                "message": user_input,
                "thread_id": st.session_state.thread_id
            },
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code != 200:
            return {
                "error": f"Backend error {response.status_code}",
                "detail": response.text
            }
            
        data = response.json()
        
        # Update thread_id if returned
        if "thread_id" in data:
            st.session_state.thread_id = data["thread_id"]
            
        return data
        
    except Exception as e:
        print(f"!!! Request failed: {str(e)}")
        return {
            "error": "Connection error",
            "detail": str(e)
        }

# Chat input
print("📝 Waiting for user input...")
if user_input := st.chat_input("Type your message here..."):
    # Add user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    
    # Process with backend
    with st.spinner("Processing..."):
        result = process_message(user_input)
    
    # Handle response
    if "error" in result:
        st.error(f"Error: {result['error']}\n\n{result.get('detail', '')}")
    else:
        # Add assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["response"]
        })
    
    st.rerun()