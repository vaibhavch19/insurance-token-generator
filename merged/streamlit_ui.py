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
if "show_upload_option" not in st.session_state:
    st.session_state.show_upload_option = False

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def process_message(user_input: str):
    payload = {"message": user_input, "thread_id": st.session_state.thread_id}
    response = requests.post(f"{BACKEND_API}/api/chat", json=payload, timeout=30)
    if response.status_code != 200:
        st.error(f"Backend error: {response.text}")
        return None
    data = response.json()
    if "upload_link" in data["response"]:
        st.session_state.show_upload_option = True
    return data

if user_input := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Processing..."):
        result = process_message(user_input)
        if result:
            st.session_state.messages.append({"role": "assistant", "content": result["response"]})
    st.rerun()

if st.session_state.show_upload_option:
    st.markdown("### Upload Accident Images")
    uploaded_files = st.file_uploader("Upload photos (JPEG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if uploaded_files and st.button("Submit Files"):
        ticket_id = next((msg["content"].split("/upload/")[1].split(" ")[0] for msg in st.session_state.messages if "upload_link" in msg["content"]), None)
        if ticket_id:
            files = [("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files]
            response = requests.post(f"{BACKEND_API}/upload/{ticket_id}", files=files)
            if response.status_code == 200:
                st.success(response.json()["message"])
            else:
                st.error(f"Upload failed: {response.text}")
        st.rerun()