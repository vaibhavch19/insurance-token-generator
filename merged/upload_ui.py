import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
DB_PATH = "fnol.db"
UPLOAD_DIR = "static/uploads"
REPORT_DIR = "static/reports"
REPORT_BASE_URL = "http://localhost:8000/static"

# Helper Functions
def summarize_image(file_path: str) -> str:
    try:
        image = Image.open(file_path)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="JPEG")
        response = gemini_model.generate_content([
            """
            Summarize the visible damage in this accident image for an insurance claim. Your response should be a short summary of the visible damage in the image.
            
            Give your output as only a string without any markdown characters or formatting.
            """,
            {"mime_type": "image/jpeg", "data": image_bytes.getvalue()}
        ])
        print(response.text)
        return response.text
    
    except Exception as e:
        return f"Error summarizing image: {e}"

def generate_report(ticket_id: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
    ticket = cursor.fetchone()
    conn.close()
    
    try:
        response = gemini_model.generate_content([
            f"""
            Generate a Claim Report for an motor accident that has happened. The report should include the following in a Markdown format:
            
            FNOL Report (Header)
            - Ticket ID: {ticket[0]}
            - Phone Number: {ticket[1]}
            - Policy Number: {ticket[2]}
            - Location: {ticket[4]}
            - Date/Time: {ticket[5]}
            
            Claim Summary (Subheader)
            - List of Image Summaries
            - User Notes (if any)
            
            Scene Recreation (Subheader)
            - Description of what might have happened based on the image summaries, user notes and other details.
            
            For your support to generate the scene recreation, the image summaries and user notes are given below:
            
            {ticket[8] or 'None'}
            
            Generate the report as a markdown and comply with the formatting making sure the report is legible.
            
            Only return the report as a string with markdown characters and formatting but not the ```markdown ``` characters.
            """
        ])
        report_text = response.text
        os.makedirs(REPORT_DIR, exist_ok=True)
        report_path = f"{REPORT_DIR}/{ticket_id}_report.md"
        with open(report_path, "w") as f:
            f.write(report_text)
        return f"{REPORT_BASE_URL}/{ticket_id}_report.md"
    
    except Exception as e:
        return f"Error summarizing image: {e}"
    

# Initialize Gemini
genai.configure(api_key=os.getenv("GOOGLE_GENERATIVE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="Upload Accident Details", page_icon="📷")
st.title("📷 Upload Accident Details")

# Get ticket_id from URL
ticket_id = st.query_params.get("ticket_id", None)

if not ticket_id:
    st.error("No ticket ID provided. Please start from the FNOL Claims Assistant.")
    st.stop()

st.markdown(f"**Ticket ID:** `{ticket_id}`")

# Upload Section
uploaded_files = st.file_uploader("Upload photos (JPEG, PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
additional_text = st.text_area("Add any additional details about the accident")

if uploaded_files or additional_text:
    if st.button("Submit and Generate Report"):
        with st.spinner("Processing uploads..."):
            os.makedirs(f"{UPLOAD_DIR}/{ticket_id}", exist_ok=True)
            summaries = []
            
            # Process uploaded images
            for file in uploaded_files:
                file_path = os.path.join(f"{UPLOAD_DIR}/{ticket_id}", file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getvalue())
                summary = summarize_image(file_path)
                summaries.append(f"{file.name}: {summary}")
            
            # Add text summary if provided
            if additional_text:
                summaries.append(f"User Notes: {additional_text}")
            
            print(summaries)
            
            # Update database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE tickets SET image_summaries = ? WHERE ticket_id = ?",
                           (json.dumps(summaries), ticket_id))
            
            if summaries:
            # Generate report
                report_link = generate_report(ticket_id)
                cursor.execute("UPDATE tickets SET report_link = ? WHERE ticket_id = ?", (report_link, ticket_id))
                conn.commit()
                conn.close()
                
                st.success("Uploads processed and report generated!")
                st.markdown(f"[View Report]({report_link})")