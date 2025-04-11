import streamlit as st
import requests
import uuid

st.set_page_config(page_title="FNOL Claims Assistant", page_icon="🚗")
st.title("🚗 FNOL Claims Assistant")

BACKEND_API = "http://localhost:8000"

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hello! I'm here to help with your insurance claim. Could you please share what happened?"
    }]
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "trigger_send" not in st.session_state:
    st.session_state.trigger_send = False


def process_message(user_input: str):
    payload = {"message": user_input, "thread_id": st.session_state.thread_id}
    response = requests.post(f"{BACKEND_API}/api/chat", json=payload, timeout=30)
    if response.status_code != 200:
        st.error(f"Backend error: {response.text}")
        return None
    return response.json()
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if user_input := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Processing..."):
        result = process_message(user_input)
    if result:
        assistant_msg = result["response"]

        if "[here](" in assistant_msg or "FNOL ticket has been created" in assistant_msg:
            st.session_state.show_upload_option = True

        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_msg
        })

    # Reset send trigger
    st.session_state.trigger_send = False
    st.rerun()