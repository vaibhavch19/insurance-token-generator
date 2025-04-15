from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
import os
from summarizer import summarize_insurance_by_phone

app = FastAPI()

@app.get("/api/policy-summary/{phone_number}")
def get_policy_summary(phone_number: str):
    print(f"📞 Received phone number: {phone_number}")
    try:
        summary = summarize_insurance_by_phone(phone_number)
        return summary
    except Exception as e:
        print("❌ Error fetching policy summary:", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch policy summary: {str(e)}")

@app.get('/api/fetch-rsa-details/<phone_number>')
def fetch_rsa_details(phone_number):
    try:
        conn = sqlite3.connect("FNOL_TICKETS.db")
        cursor = conn.cursor()

        # Fetch the latest FNOL ticket for this phone number
        cursor.execute("""
            SELECT RSA_included, ticket_id
            FROM fnol_details
            WHERE phone_number = ?
            ORDER BY ticket_date_time DESC
            LIMIT 1
        """, (phone_number,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return {"error": "No FNOL entry found for this phone number"}, 404

        rsa_included, ticket_id = row

        if rsa_included.lower() in ['yes', 'true', '1']:
            return {
                "rsa_included": True,
                "ticket_id": ticket_id,
                "services": ["towing", "cab", "fuel delivery"]  # hardcoded or modify as needed
            }
        else:
            return {
                "rsa_included": False,
                "ticket_id": ticket_id,
                "services": []
            }

    except Exception as e:
        return {"error": "Failed to fetch RSA details", "details": str(e)}, 500



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

# Define the request schema using Pydantic
class FNOLPayload(BaseModel):
    phone_number: str
    policy_number: str
    location: str
    accident_date_time: str

# API Endpoint to create an FNOL entry
@app.post("/create_fnol_ticket_tool/")
def create_fnol_entry(data: FNOLPayload):
    try:
        print("📥 Incoming FNOL data:", data.dict())

        ticket_id = str(uuid4())
        ticket_date_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        try:
            conn = sqlite3.connect("FNOL_TICKETS.db")
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO fnol_details (ticket_id, phone_number, policy_number, location, 
                                             accident_date_time, ticket_date_time)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    ticket_id,
                    data.phone_number,
                    data.policy_number,
                    data.location,
                    data.accident_date_time,
                    ticket_date_time,
                ),
            )
            conn.commit()
        except Exception as db_err:
            conn.rollback()
            print("❌ Database insert failed:", str(db_err))
            raise HTTPException(status_code=500, detail=f"Database insert failed: {str(db_err)}")
        finally:
            conn.close()

        print("✅ FNOL entry successfully created:", ticket_id)
        upload_link = f"http://localhost:8501/image_summary_flow?ticket_id={ticket_id}"
        return {
            "message": "FNOL Entry Created",
            "ticket_id": ticket_id,
            "phone_number": data.phone_number,
            "policy_number": data.policy_number,
            "location": data.location,
            "accident_date_time": data.accident_date_time,
            "ticket_date_time": ticket_date_time,
            "upload_link": upload_link
        }

    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print("❌ Error in create_fnol_entry:", err)
        raise HTTPException(status_code=500, detail=str(e))
