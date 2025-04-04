import streamlit as st
import websocket
import threading
import json

st.title("FNOL Chatbot")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

def on_message(ws, message):
    st.session_state["messages"].append({"text": message, "sender": "bot"})
    st.experimental_rerun()

def on_open(ws):
    st.session_state["ws"] = ws

def start_websocket():
    ws = websocket.WebSocketApp("ws://your-backend-url",
                                on_message=on_message,
                                on_open=on_open)
    ws.run_forever()

if "ws_thread" not in st.session_state:
    st.session_state["ws_thread"] = threading.Thread(target=start_websocket, daemon=True)
    st.session_state["ws_thread"].start()

for msg in st.session_state["messages"]:
    alignment = "user" if msg["sender"] == "user" else "bot"
    st.chat_message(alignment, msg["text"])

user_input = st.text_input("Type a message", key="user_input")
if st.button("Send") and user_input:
    st.session_state["messages"].append({"text": user_input, "sender": "user"})
    if "ws" in st.session_state:
        st.session_state["ws"].send(user_input)
    st.experimental_rerun()
