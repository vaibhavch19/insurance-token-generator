from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
import requests
import json
import os
import uvicorn 
from summarizer import summarize_insurance_by_phone
app = FastAPI()

# Allow frontend to access backend APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
connections = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    # try:
    while True:
        data = await websocket.receive_text()
        print(f"Received: {data}")

        # Example processing
        if data.replace(" ", "").isalnum():  # Allows numbers and letters
            policy_summary = summarize_insurance_by_phone(data)
            response = json.dumps(policy_summary)
        else:
            response = "Please provide a valid phone number or policy number."


        await websocket.send_text(response)
    # except WebSocketDisconnect:
    #     connections.remove(websocket)

@app.get("/api/policy-summary/{phone_number}")
def get_policy_summary(phone_number: str):
    print(f'{phone_number = }')
    # try:
    #     summarizer_url = f"http://policy-summarizer-url/api/summary/{policy_id}"
    #     response = requests.get(summarizer_url)
    #     return response.json()
    # except Exception as e:
    #     return {"error": "Failed to fetch policy summary", "details": str(e)}
    return summarize_insurance_by_phone(phone_number)


@app.get("/api/policy-summary/{phone_number}")
async def get_policy_summary(phone_number: str):
    return summarize_insurance_by_phone(phone_number)

@app.post("/api/raise_ticket")
async def raise_ticket(data: dict):
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
@app.post("/create_fnol/")
def create_fnol_entry(data: FNOLRequest):
    ticket_id = str(uuid4())  # Generate unique ticket ID
    ftp_link = create_ftp_directory(ticket_id)  # Generate FTP upload folder
    report_link = None
    ticket_date_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")  # Capture API call timestamp

    # Connect to motor_insurance_policy.db
    conn = sqlite3.connect("motor_insurance_policy.db")
    cursor = conn.cursor()

    # Insert FNOL entry
    cursor.execute(
        """INSERT INTO fnol_details (ticket_id, phone_number, policy_number, ftp_link, report_link, location, 
                                     accident_date_time, ticket_date_time)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (ticket_id, data.phone_number, data.policy_number, ftp_link, report_link, data.location, 
         data.accident_date_time, ticket_date_time)
    )
    
    conn.commit()
    conn.close()

    # Return response with all details
    return {
        "message": "FNOL Entry Created",
        "ticket_id": ticket_id,
        "phone_number": data.phone_number,
        "policy_number": data.policy_number,
        "location": data.location,
        "ftp_link": ftp_link,
        "report_link": report_link,
        "accident_date_time": data.accident_date_time,
        "ticket_date_time": ticket_date_time
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
