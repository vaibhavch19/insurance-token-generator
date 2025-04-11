import streamlit as st
import requests
from config import FLASK_HOST, FLASK_PORT

st.title("🚗 FNOL Motor Insurance Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "state" not in st.session_state:
    st.session_state.state = None

# Mobile number input
if not st.session_state.state:
    mobile_number = st.text_input("Enter your registered mobile number (try '1234567890' for demo)")
    if st.button("Start Claim"):
        try:
            url = f"http://{FLASK_HOST}:{FLASK_PORT}/start"
            payload = {"mobile_number": mobile_number}
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            st.write(f"Debug: Full response from /start: {data}")  # Log the raw response
            if "messages" not in data:
                st.error("Error: 'messages' key missing in response")
                raise KeyError("'messages' key not found in response")
            st.session_state.messages.append({"role": "assistant", "content": "\n".join(data["messages"])})
            st.session_state.state = data["state"]
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {e}")
            st.write(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
        except (ValueError, KeyError) as e:
            st.error(f"Response parsing failed: {e}")
            st.write(f"Raw response: {response.text if 'response' in locals() else 'No response'}")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input and file upload
if st.session_state.state:
    user_input = st.chat_input("Your response")
    if user_input:
        try:
            response = requests.post(f"http://{FLASK_HOST}:{FLASK_PORT}/respond",
                                     json={"user_input": user_input, "state": st.session_state.state})
            response.raise_for_status()
            data = response.json()
            st.write(f"Debug: Full response from /respond: {data}")  # Log the raw response
            if "messages" not in data:
                st.error("Error: 'messages' key missing in response")
                raise KeyError("'messages' key not found in response")
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.messages.append({"role": "assistant", "content": "\n".join(data["messages"])})
            st.session_state.state = data["state"]
            st.rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"Error sending response: {e}")
            st.write(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
        except (ValueError, KeyError) as e:
            st.error(f"Response parsing failed: {e}")
            st.write(f"Raw response: {response.text if 'response' in locals() else 'No response'}")

    if st.session_state.state.get("ticket_id"):
        uploaded_files = st.file_uploader("Upload photos/text", accept_multiple_files=True)
        if uploaded_files and st.button("Submit Files"):
            files = {f.name: f for f in uploaded_files}
            requests.post(f"http://{FLASK_HOST}:{FLASK_PORT}/upload/{st.session_state.state['ticket_id']}",
                          files=files)
            st.success("Files uploaded!")