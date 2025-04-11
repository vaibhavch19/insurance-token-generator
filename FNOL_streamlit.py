import streamlit as st
import requests
import os
import google.generativeai as genai
from PIL import Image
import io
# Configure Gemini first (✅ moved to the top)
genai.configure(api_key="AIzaSyAs2IUf5H9I1m9GQ8flGoj0KmAAPCu5DIE")  # ✅ string
gemini_model = genai.GenerativeModel("models/gemini-1.5-flash")


def summarize_image_with_gemini(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="JPEG")
        image_bytes.seek(0)

        response = gemini_model.generate_content([
            "Summarize the visible damage in this accident image for an insurance claim:",
            image
        ])
        return response.text
    except Exception as e:
        return f" Gemini failed to summarize `{uploaded_file.name}`: {e}"


# App setup
st.set_page_config(page_title="FNOL Chatbot", page_icon="🆘")
st.title(" FNOL Claims Assistant")

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
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "trigger_send" not in st.session_state:
    st.session_state.trigger_send = False


def process_message(user_input: str):
    try:
        response = requests.post(
            f"{BACKEND_API}/api/chat",
            json={"message": user_input, "thread_id": st.session_state.thread_id},
            timeout=30
        )
        if response.status_code != 200:
            return {"error": f"Backend error {response.status_code}", "detail": response.text}
        data = response.json()
        if "thread_id" in data:
            st.session_state.thread_id = data["thread_id"]
        return data
    except Exception as e:
        return {"error": "Connection error", "detail": str(e)}


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
# Chat input
user_input = st.chat_input("Type your message here...")
if user_input:
    st.session_state.user_input = user_input
    st.session_state.trigger_send = True
    st.rerun()
#st.session_state.show_upload_option = True  # TEMP: Always show image upload section
# ✅ Inline image upload flow after FNOL ticket creation
#################
if st.session_state.trigger_send:
    user_input = st.session_state.user_input
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Processing..."):
        result = process_message(user_input)

    if "error" in result:
        st.error(f"Error: {result['error']}\n\n{result.get('detail', '')}")
    else:
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


################
if st.session_state.get("show_upload_option"):
    st.markdown(" Upload Images of the Accident")

    uploaded_files = st.file_uploader(
        "Upload photos related to the accident (JPEG, PNG)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    if uploaded_files:
        summaries = []
        for file in uploaded_files:
            st.image(file, caption=file.name, use_column_width=True)
            with st.spinner(f"Summarizing {file.name}..."):
                summary = summarize_image_with_gemini(file)
                summaries.append(f"**{file.name}** → {summary}")

        if summaries:
            st.markdown(" AI Summary sof Uploaded Images:")
            for summary in summaries:
                st.success(summary)