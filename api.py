from flask import Flask, request
from flask_cors import CORS
import sqlite3
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
import requests
import json
import os
import uvicorn
from summarizer import summarize_insurance_by_phone


app = Flask(__name__)
CORS(app)


@app.get("/api/policy-summary/<phone_number>")
def get_policy_summary(phone_number):
    print(f"Received phone number: {phone_number}")
    try:
        summary = summarize_insurance_by_phone(phone_number)
        return summary
    
    except Exception as e:
        return {"error": f"Failed to fetch policy summary.\n{str(e)}"}, 500

@app.get('/api/fetch-rsa-details/<phone_number>')
def fetch_rsa_details(phone_number):
    


@app.post("/api/raise_ticket")
def raise_ticket(data: dict):
    """Submit a ticket with policy ID and incident details"""
    try:
        policy_id = data.get("policyId")
        incident_details = data.get("incidentDetails")
        return {
            "success": True,
            "message": "ticket raised successfully",
            "policyId": policy_id,
            "incidentDetails": incident_details,
        }
    except Exception as e:
        return {"error": "Failed to submit claim", "details": str(e)}


# Define request model
class FNOLRequest(BaseModel):
    phone_number: str
    policy_number: str
    location: str
    accident_date_time: str  # User-provided accident date-time


# Function to create an FTP directory
def create_ftp_directory(ticket_id):
    ftp_base_path = "ftp_server/fnol_uploads"  # Root directory for FNOL uploads
    ftp_folder_path = os.path.join(ftp_base_path, ticket_id)

    # Create directory if it doesn't exist
    os.makedirs(ftp_folder_path, exist_ok=True)

    return f"ftp://your-ftp-server.com/fnol_uploads/{ticket_id}/"


# API Endpoint to create an FNOL entry
@app.post("/create_fnol/",)
def create_fnol_entry():
    try:
        data = request.get_json()
        print("📥 Incoming FNOL data:", data)

        # Defensive field extraction
        try:
            phone_number = data["phone_number"]
            policy_number = data["policy_number"]
            location = data["location"]
            accident_date_time = data["accident_date_time"]
        except KeyError as e:
            missing = str(e).strip("'")
            print(f"❌ Missing required field: {missing}")
            return {"error": f"Missing required field: {missing}"}, 400

        # Generate ticket ID and other details
        ticket_id = str(uuid4())
        # ftp_link = create_ftp_directory(ticket_id)
        # report_link = None
        ticket_date_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Insert into database
        try:
            conn = sqlite3.connect("FNOL_TICKETS.db")
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO fnol_details (ticket_id, phone_number, policy_number, location, 
                                             accident_date_time, ticket_date_time)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ticket_id,
                    phone_number,
                    policy_number,
                    location,
                    accident_date_time,
                    ticket_date_time,
                ),
            )
            conn.commit()
        except Exception as db_err:
            conn.rollback()
            print("❌ Database insert failed:", str(db_err))
            return {"error": "Database insert failed", "details": str(db_err)}, 500
        finally:
            conn.close()

        # Success response
        print("✅ FNOL entry successfully created:", ticket_id)
        upload_link = f"http://localhost:8501/image_summary_flow?ticket_id={ticket_id}"
        return {
            "message": "FNOL Entry Created",
            "ticket_id": ticket_id,
            "phone_number": phone_number,
            "policy_number": policy_number,
            "location": location,
            "accident_date_time": accident_date_time,
            "ticket_date_time": ticket_date_time,
            "upload_link": upload_link
        }

    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print("❌ Error in create_fnol_entry:", err)
        print("❌ Unexpected error:", str(e))
        return {"error": "Internal Server Error", "details": str(e)}, 500

if __name__ == "__main__":
    app.run()
