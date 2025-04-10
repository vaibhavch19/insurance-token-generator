from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from typing import Annotated, Optional, Dict, List
from datetime import datetime
import sqlite3
import os
import json
import logging
import google.generativeai as genai
from PIL import Image
import io
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Configuration
DB_PATH = "fnol.db"
UPLOAD_DIR = "static/uploads"
API_URL = "http://localhost:8000"

# Initialize Gemini
genai.configure(api_key="AIzaSyAs2IUf5H9I1m9GQ8flGoj0KmAAPCu5DIE")
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    api_key="AIzaSyAs2IUf5H9I1m9GQ8flGoj0KmAAPCu5DIE",
    model="gemini-1.5-flash",
    temperature=0.7,
    max_tokens=100,
)

# State Definition
class State(BaseModel):
    messages: Annotated[List, add_messages] = []
    phone_number: Optional[str] = None
    policy_number: Optional[str] = None
    rsa: Optional[bool] = None
    accident_date: Optional[str] = None
    accident_time: Optional[str] = None
    accident_location: Optional[str] = None
    accident_details: Optional[str] = None
    ticket_id: Optional[str] = None
    upload_link: Optional[str] = None
    ticket_created: Optional[bool] = False
    awaiting_confirmation: Optional[bool] = False
    image_summaries: Optional[List[str]] = None

# Database Setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            phone_number TEXT PRIMARY KEY,
            policy_number TEXT,
            rsa_available INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            phone_number TEXT,
            policy_number TEXT,
            accident_details TEXT,
            location TEXT,
            accident_date_time TEXT,
            timestamp TEXT,
            status TEXT,
            image_summaries TEXT
        )
    """)
    # Insert sample data
    cursor.execute("INSERT OR IGNORE INTO policies (phone_number, policy_number, rsa_available) VALUES (?, ?, ?)",
                   ("9876543210", "POLICY123", 1))
    conn.commit()
    conn.close()

# Tools
@tool
def get_policy_summary(phone_number: str) -> Dict:
    '''Fetch policy summary given the user's phone number'''
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT policy_number, rsa_available FROM policies WHERE phone_number = ?", (phone_number,))
    result = cursor.fetchone()
    conn.close()
    if result:
        policy_number, rsa = result
        return {
            "message": f"Policy found: {policy_number}, RSA: {'Yes' if rsa else 'No'}",
            "policy_number": policy_number,
            "rsa": bool(rsa)
        }
    raise ValueError("No policy found for this phone number")

@tool
def create_fnol_ticket(phone_number: str, policy_number: str, location: str, accident_date_time: str) -> Dict:
    '''Raise a FNOL ticket using the user's phone number, policy number, accident location, and date-time'''
    ticket_id = str(uuid.uuid4())[:8]
    upload_link = f"{API_URL}/upload/{ticket_id}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets (ticket_id, phone_number, policy_number, location, accident_date_time, timestamp, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Open')
    """, (ticket_id, phone_number, policy_number, location, accident_date_time, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {"ticket_id": ticket_id, "upload_link": upload_link, "ticket_created": True}

tools = [get_policy_summary, create_fnol_ticket]
llm_with_tools = llm.bind_tools(tools)

# Agent Logic
def agent_node(state: State) -> Dict:
    system_prompt = f"""
    You are an insurance assistant for FNOL claims. Current date: {datetime.now().strftime('%Y-%m-%d')}.
    Steps:
    1. Ask for phone number if not provided.
    2. Fetch policy details using get_policy_summary.
    3. Ask for accident details (date, time, location, description).
    4. Present summary for confirmation.
    5. Create ticket with create_fnol_ticket after confirmation.
    6. Provide upload link and wait for images.
    """
    messages = state.messages
    last_message = messages[-1].content.lower() if messages else ""

    if not state.phone_number:
        if phone_number := extract_phone_number(last_message):
            return {"phone_number": phone_number, "tool_calls": [{"name": "get_policy_summary", "args": {"phone_number": phone_number}}]}
        return {"messages": [AIMessage(content="Please provide your registered phone number.")]}

    if state.policy_number and not state.accident_location:
        return {"messages": [AIMessage(content="Please provide the accident location, date, time, and details.")]}
    
    if all([state.accident_location, state.accident_date, state.accident_time, state.accident_details]) and not state.ticket_created:
        summary = f"Confirm: Phone: {state.phone_number}, Policy: {state.policy_number}, Location: {state.accident_location}, Date: {state.accident_date}, Time: {state.accident_time}, Details: {state.accident_details}"
        return {"messages": [AIMessage(content=summary)], "awaiting_confirmation": True}

    if state.awaiting_confirmation and ("yes" in last_message or "confirm" in last_message):
        accident_date_time = f"{state.accident_date} {state.accident_time}"
        return {
            "tool_calls": [{
                "name": "create_fnol_ticket",
                "args": {"phone_number": state.phone_number, "policy_number": state.policy_number, "location": state.accident_location, "accident_date_time": accident_date_time}
            }]
        }

    if state.ticket_created and state.upload_link and not state.image_summaries:
        return {"messages": [AIMessage(content=f"Please upload images at {state.upload_link}")]}
    
    if state.image_summaries:
        return {"messages": [AIMessage(content=f"Images summarized: {', '.join(state.image_summaries)}. All done!")]}

    response = llm_with_tools.invoke(messages + [SystemMessage(content=system_prompt)])
    return {"messages": [response]}

# Graph Setup
builder = StateGraph(State)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")
builder.add_edge("agent", END)
graph = builder.compile(checkpointer=MemorySaver())

# API Endpoints
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    logger.info(f"Received chat request: {request.message}")
    human_message = HumanMessage(content=request.message)
    thread_id = request.thread_id or str(uuid.uuid4())
    result = graph.invoke({"messages": [human_message]}, {"configurable": {"thread_id": thread_id}})
    last_message = result["messages"][-1]
    return {"response": last_message.content, "thread_id": thread_id}

@app.post("/upload/{ticket_id}")
async def upload_files(ticket_id: str, files: List[UploadFile] = File(...)):
    os.makedirs(f"{UPLOAD_DIR}/{ticket_id}", exist_ok=True)
    summaries = []
    for file in files:
        file_path = os.path.join(f"{UPLOAD_DIR}/{ticket_id}", file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.file.read())
        summary = summarize_image(file_path)
        summaries.append(summary)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET image_summaries = ? WHERE ticket_id = ?", (json.dumps(summaries), ticket_id))
    conn.commit()
    conn.close()
    
    graph.update_state({"configurable": {"thread_id": thread_id}}, {"image_summaries": summaries})
    return {"message": f"Uploaded and summarized {len(summaries)} files"}

# Helper Functions
def extract_phone_number(text: str) -> Optional[str]:
    import re
    match = re.search(r"\b\d{10}\b", text)
    return match.group(0) if match else None

def summarize_image(file_path: str) -> str:
    try:
        image = Image.open(file_path)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="JPEG")
        response = gemini_model.generate_content([
            "Summarize the visible damage in this accident image for an insurance claim:",
            {"mime_type": "image/jpeg", "data": image_bytes.getvalue()}
        ])
        return response.text
    except Exception as e:
        logger.error(f"Image summarization failed: {e}")
        return f"Error summarizing image: {e}"

if __name__ == "__main__":
    init_db()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)