import streamlit as st
import requests
import websocket
import threading

st.title("FNOL Chatbot")

# WebSocket server URL (ensure backend is running)
# WS_URL = "ws://localhost:8000/ws"
API_URL = 'http://0.0.0.0:8000'

# Store messages in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# # WebSocket message handler
# def on_message(ws, message):
#     st.session_state["messages"].append({"text": message, "sender": "bot"})
#     st.rerun()

# # WebSocket connection handler
# def on_open(ws):
#     st.session_state["ws"] = ws

# # Start WebSocket connection thread
# def start_websocket():
#     ws = websocket.WebSocketApp(
#         WS_URL,
#         on_message=on_message,
#         on_open=on_open
#     )
#     ws.run_forever()

# Initialize WebSocket connection once
# if "ws_thread" not in st.session_state:
#     st.session_state["ws_thread"] = threading.Thread(target=start_websocket, daemon=True)
#     st.session_state["ws_thread"].start()

# Display conversation
for msg in st.session_state["messages"]:
    alignment = "user" if msg["sender"] == "user" else "bot"
    with st.chat_message(alignment):
        st.write(msg["text"])

# User input and send message
user_input = st.text_input("Type a message", key="user_input")
if st.button("Send") and user_input:
    st.session_state["messages"].append({"text": user_input, "sender": "user"})
    
    try:
        response = requests.get(f'{API_URL}/api/policy-summary/{user_input}')
        st.session_state["messages"].append({"text": str(response.text), "sender": "bot"})
    except Exception as e:
        st.error(f"Error: {e}")

    st.rerun()  # Updated from st.experimental_rerun()
