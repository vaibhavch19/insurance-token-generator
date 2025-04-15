from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from summarizer import summarize_insurance_by_phone
app = FastAPI()

DATABASE = 'motor_insurance_policy.db'

class FNOLRequest(BaseModel):
    policy_number: str
    accident_date: str
    accident_time: str
    accident_location: str
    description: str
    rsa_required: Optional[bool] = False
    rsa_service: Optional[str] = None

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def summarize_insurance_by_phone(phone_number: str) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM policies WHERE phone_number = ?", (phone_number,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise Exception("No policy found for the given phone number.")

    summary = {
        "Policy Holder": row["policy_holder"],
        "Policy Number": row["policy_number"],
        "Phone Number": row["phone_number"],
        "Vehicle": f"{row['vehicle_make']} {row['vehicle_model']} ({row['vehicle_year']})",
        "RSA Included": bool(row["rsa_included"]),
        "Policy Start Date": row["start_date"],
        "Policy End Date": row["end_date"],
    }
    return summary

@app.get("/api/policy-summary/{phone_number}")
def get_policy_summary_by_phone(phone_number: str):
    print(f"Received phone number: {phone_number}")
    try:
        summary = summarize_insurance_by_phone(phone_number)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch policy summary.\n{str(e)}")

@app.get("/get_policy_by_phone")
def get_policy_by_phone(phone: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM policies WHERE phone_number = ?", (phone,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {key: row[key] for key in row.keys()}
    else:
        raise HTTPException(status_code=404, detail="Policy not found for the given phone number.")

@app.get("/get_policy_summary")
def get_policy_summary(policy_number: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM policies WHERE policy_number = ?", (policy_number,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {key: row[key] for key in row.keys()}
    else:
        raise HTTPException(status_code=404, detail="Policy not found")

@app.post("/create_fnol/")
def create_fnol(data: FNOLRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tickets (policy_number, accident_date, accident_time, accident_location, description, rsa_required, rsa_service)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.policy_number,
            data.accident_date,
            data.accident_time,
            data.accident_location,
            data.description,
            int(data.rsa_required),
            data.rsa_service,
        )
    )
    conn.commit()
    ticket_id = cursor.lastrowid
    conn.close()

    return {
        "ticket_id": ticket_id,
        "message": "FNOL ticket created successfully",
        "ftp_upload_link": f"http://localhost:8000/upload/{ticket_id}"
    }
