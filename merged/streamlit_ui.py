import streamlit as st
import requests
import uuid

st.set_page_config(page_title="FNOL Claims Assistant", page_icon="🚗")
st.title("🚗 FNOL Claims Assistant")

BACKEND_API = "http://localhost:8000"

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist with your claim today?"}]
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def process_message(user_input: str):
    payload = {"message": user_input, "thread_id": st.session_state.thread_id}
    response = requests.post(f"{BACKEND_API}/api/chat", json=payload, timeout=30)
    if response.status_code != 200:
        st.error(f"Backend error: {response.text}")
        return None
    return response.json()

if user_input := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Processing..."):
        result = process_message(user_input)
        if result:
            st.session_state.messages.append({"role": "assistant", "content": result["response"]})
    st.rerun()