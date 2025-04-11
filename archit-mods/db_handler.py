import sqlite3
import os
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            mobile_number VARCHAR(15) PRIMARY KEY,
            policy_id VARCHAR(50),
            policy_pdf_path VARCHAR(255),
            rsa_available BOOLEAN
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id VARCHAR(50) PRIMARY KEY,
            mobile_number VARCHAR(15),
            accident_details TEXT,
            timestamp DATETIME,
            status VARCHAR(20)
        )
    """)
    # Insert sample policy for testing
    cursor.execute("INSERT OR IGNORE INTO policies VALUES (?, ?, ?, ?)",
                   ("1234567890", "POL001", "static/policies/sample.pdf", True))
    conn.commit()
    conn.close()

def get_policy_details(mobile_number):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM policies WHERE mobile_number = ?", (mobile_number,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"policy_id": row[1], "policy_pdf_path": row[2], "rsa_available": row[3]}
    raise ValueError("Policy not found.")

def create_ticket(mobile_number, accident_details):
    import uuid
    ticket_id = str(uuid.uuid4())[:8]  # Shortened for readability
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tickets (ticket_id, mobile_number, accident_details, timestamp, status) VALUES (?, ?, ?, datetime('now'), 'Open')",
                   (ticket_id, mobile_number, accident_details))
    conn.commit()
    conn.close()
    return ticket_id