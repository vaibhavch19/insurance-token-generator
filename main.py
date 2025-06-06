from typing import List, Dict, Optional, Annotated
from typing_extensions import TypedDict
from typing import Dict, List, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.tools import tool, Tool
# from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
import os
import json
from dotenv import load_dotenv
from datetime import datetime
from summarizer import summarize_insurance_by_phone
from fastapi import FastAPI
from fastapi import Request
app = FastAPI()
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n[REQUEST] {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    try:
        body = await request.json()
        print(f"Body: {body}")
    except:
        pass
    
    response = await call_next(request)
    return response
load_dotenv()

API_URL = 'http://127.0.0.1:5050/api'

# ========== STATE ==========
class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    name: Optional[str]

    phone_number: Optional[str]
    policy_number: Optional[str]
    rsa: Optional[bool]
    accident_date: Optional[str]
    accident_time: Optional[str]
    accident_location: Optional[str]
    accident_details: Optional[str]
    towing_service: Optional[bool]
    cab_service: Optional[bool]
    ftp_link: Optional[str]
    scene_recreation: Optional[bool]
    accident_summary: Optional[str]
    ticket_id: Optional[str]
    ticket_created: Optional[bool]
    ticket_details: Optional[Dict]
    awaiting_confirmation: Optional[bool]
    # New flag to track confirmation state

# ========== LLM ==========
# llm = AzureChatOpenAI(
#     api_key=os.getenv('AZURE_OPENAI_API_KEY'),
#     api_version='2023-06-01-preview',
#     azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
#     temperature=0.7
# )

llm = ChatGoogleGenerativeAI(
    api_key=os.getenv('GOOGLE_GENERATIVE_API_KEY'),
    model='gemini-1.5-flash',
    temperature=0.7,
    
)

# ========== TOOLS ==========
@tool
def get_policy_summary(phone_number: str) -> dict:
    """Fetch policy details using the user's phone number"""
    try: 
        response = requests.get(f"{API_URL}/policy-summary/{phone_number}")
        summary = response.json() if response.status_code == 200 else {}
        
        return {
                "message": f"""Here are your policy details:

- Policy Number: {summary.get("policy_number")}
- Policy Type: {summary.get("policy_type")}
- Validity: {summary.get("policy_valid")}
- Deductible: {summary.get("deductible")}
- Liability: {summary.get("liability_amount")}
- RSA: {summary.get("RSA")}
- Other Claims: {", ".join(summary.get("other_claims")) if "other_claims" in summary else "None"}

Please confirm if these details are correct.""",
                "policy_number": summary.get("policy_number"),
                "rsa": summary.get("RSA")
            }
    
    except Exception as e:
        return {"message": f"❌ Error fetching policy summary: {e}"}

@tool
def fetch_RSA_details(policy_number: str) -> Dict:
    """Fetch if RSA is included in the policy"""
    response = requests.post(
        f"{API_URL}/fetch-rsa-details", json={"policy_number": policy_number}
    )
    rsa_details = (
        response.json().get("rsa_details", {}) if response.status_code == 200 else {}
    )
    return {"rsa_details": rsa_details}


# @tool
# def collect_accident_details(date_time: str, location: str, description: str) -> dict:
#     """
#     Extract accident details to proceed with claim creation.
#     """
#     return {
#         "accident_date_time": date_time,
#         "location": location,
#         "accident_description": description,
#     }

@tool
def raise_ticket(state: State) -> Dict:
    """Book an appointment with all collected details"""
    if not state.get("ticket_created", False):
        return {"error": "Ticket not created yet"}
    if not state.get("awaiting_confirmation", False):
        return {"error": "Confirmation not received"}
    if not state.get("accident_summary", False):
        return {"error": "Accident summary not provided"}

    if not state.get("accident_location", False):
        return {"error": "Accident location not provided"}
    if not state.get("accident_date", False):
        return {"error": "Accident date not provided"}
    if not state.get("accident_time", False):
        return {"error": "Accident time not provided"}
    if not state.get("accident_details", False):
        return {"error": "Accident details not provided"}

    response = requests.post(
        f"{API_URL}/ticket_raising",
        json={
            "phone_number": state["phone_number"],
            "policy_number": state["policy_number"],
            "rsa": state["rsa"],
            "accident_date": state["accident_date"],
            "accident_time": state["accident_time"],
            "accident_location": state["accident_location"],
            "accident_details": state["accident_details"],
            "towing_service": state["towing_service"],
            "cab_service": state["cab_service"],
            "ftp_link": state["ftp_link"],
            "scene_recreation": state["scene_recreation"],
            "accident_summary": state["accident_summary"],
            "ticket_id": state["ticket_id"],
            "ticket_created": state["ticket_created"],
            "awaiting_confirmation": state["awaiting_confirmation"],
        },
    )
    result = (
        response.json() if response.status_code == 200 else {"error": "Booking failed"}
    )
    return result

# Actual function to create the FNOL ticket with headers
@tool
def create_fnol_ticket_tool(
    phone_number: str,
    policy_number: str,
    location: str,
    accident_date_time: str
) -> Dict:
    """
    Create FNOL ticket using the user's phone number, policy number, accident location, and date-time.
    Returns ticket details including FTP upload link for documents and ticket ID.
    """
    try:
        fnol_data = {
            "phone_number": phone_number,
            "policy_number": policy_number,
            "location": location,
            "accident_date_time": accident_date_time,
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post("http://localhost:5050/create_fnol/", json=fnol_data, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return {
                "ticket_created": True,
                "ftp_link": data.get("ftp_link"),
                "ticket_id": data.get("ticket_id"),
                "ticket_details": data,
            }
        else:
            return {
                "error": "Failed to create FNOL entry",
                "details": response.text,
                "ticket_created": False,
            }

    except Exception as e:
        return {"error": str(e), "ticket_created": False}


# Add to tools list
tools = [
    get_policy_summary, 
    fetch_RSA_details, 
    raise_ticket, 
    create_fnol_ticket_tool  # Make sure this is properly registered
]
llm_with_tools = llm.bind_tools(tools)
import re


# Helper function to detect phone numbers
def extract_phone_number(text: str) -> Optional[str]:
    match = re.search(r"\b\d{10}\b", text)
    return match.group(0) if match else None


############################
def agent_node(state: State) -> Dict:
    print("🧠 [DEBUG] agent_node called with state:")
    print(json.dumps(state, indent=2, default=str))
    messages = state["messages"]
    last_message = messages[-1].content.lower() if messages else ""
     # System prompt for LLM
    system_prompt = f"""
    You are a helpful insurance assistant helping users file accident claims.
    Start by greeting the user.
    When the user mentions an accident or claim, politely ask for their phone number so you can fetch their policy details.
    Once phone number is provided, call the `get_policy_summary` tool to retrieve policy info. Wait for confirmation from user.
    If RSA is included in the policy, ask the user if they require towing or cab services.
        
        - ask for users a nearby location where the accident happened.
        - create a ticket and send it to the user.
        - send user a FTP link for a summary of accident with pictures or videos.
        
        
        Current state:
        Phone Number: {state.get('phone_number', 'Not provided')}
        Policy Number: {state.get('policy_number', 'Not provided')}
        RSA: {state.get('rsa', 'Not provided')}
        Accident Date: {state.get('accident_date', 'Not provided')}
        Accident Time: {state.get('accident_time', 'Not provided')}
        Accident Location: {state.get('accident_location', 'Not provided')}
        Accident Details: {state.get('accident_details', 'Not provided')}
        Towing Service: {state.get('towing_service', 'Not provided')}
        Cab Service: {state.get('cab_service', 'Not provided')}
        FTP Link: {state.get('ftp_link', 'Not provided')}
        Accident Summary: {state.get('accident_summary', 'Not provided')}
        Ticket Created: {state.get('ticket_created', False)}
        Ticket ID: {state.get('ticket_id', 'Not provided')}
        Awaiting Confirmation: {state.get('awaiting_confirmation', False)}

        Rules:
        1. Collect all required details (mobile number, policy number, RSA if needed, date, time) before creating a ticket. In fact, you can start by capturing the name and phone number and policy number.
        2. After collecting all details via save_accident_details, present the scene recreation to the user for confirmation.
        3. Only call create_fnol_ticket_tool after explicit user confirmation (e.g., 'yes' or 'confirm').
        4. If user says 'no' or requests changes during confirmation, ask what to modify.
        5. After successful ticket raising, ask if they need more help.
        6. Provide upload link to a separate page for further processing.
        7. If asked about unrelated topics, politely refuse and redirect to ticket raising.
        Current date: {datetime.now().strftime('%Y-%m-%d')}
        """
    last_message = (
            messages[-1].content.lower()
            if messages and isinstance(messages[-1], HumanMessage)
            else ""
        )
    # 🟡 If all accident details are present and awaiting confirmation
    if (
        state.get("accident_date") and
        state.get("accident_time") and
        state.get("accident_location") and
        state.get("accident_details") and
        not state.get("ticket_created") and
        not state.get("create_fnol_ticket_tool") and
        state.get("awaiting_confirmation")
    ):
        if "yes" in last_message or "confirm" in last_message:
            return {
            "state": {
                **state,
                "awaiting_confirmation": False,  # Reset confirmation flag
            },
            "messages": [
                AIMessage(content="✅ Got your confirmation! Creating your FNOL ticket now...")
            ],
            "next": "create_fnol_ticket_tool",  # ✅ Triggers ticket creation tool
        }
    elif "no" in last_message:
        return {
            "messages": [
                AIMessage(content="❌ Okay, what would you like to change before creating the ticket?")
            ]
        }

    # 💡 Handle returned FNOL ticket creation result
    ticket_result = state.get("create_fnol_ticket_tool")
    # Check if the ticket was created successfully    
    if ticket_result:
        if ticket_result.get("ticket_created"):
            return {
                "messages": [
                    AIMessage(
                        content=f"🎟️ Your FNOL ticket has been created successfully!\n\n"
                                f"• Ticket ID: {ticket_result['ticket_id']}\n"
                                f"• Upload Link: {ticket_result['ftp_link']}\n\n"
                                f"Please upload any images or videos of the accident there."
                    )
                ],
                "state": {
                    **state,
                    "ticket_created": True,
                    "ticket_id": ticket_result["ticket_id"],
                    "ftp_link": ticket_result["ftp_link"],
                    "ticket_details": ticket_result,
                },
            }
        else:
            return {
                "messages": [
                    AIMessage(content="❌ Failed to create the FNOL ticket. Please try again later.")
                ]
            }
    policy_result = state.get("get_policy_summary")
    if policy_result:
        try:
            # Extract from the text using regex
            import re

            policy_number_match = re.search(r"Policy Number:\s*(\w+)", policy_result)
            rsa_match = re.search(r"RSA:\s*(True|False)", policy_result)

            if policy_number_match:
                state["policy_number"] = policy_number_match.group(1)
            if rsa_match:
                state["rsa"] = rsa_match.group(1).lower() == "true"

            print("✅ [DEBUG] Extracted policy_number and rsa from summary")
        except Exception as e:
            print(f"❌ [DEBUG] Error parsing policy result: {e}") 
    
    if not state.get("phone_number"):
        extracted_phone = extract_phone_number(last_message)
        if extracted_phone:
            print(f"[DEBUG] Extracted phone number: {extracted_phone}")
            return {
                "messages": [
                    AIMessage(content=f"Thanks! I found your phone number: {extracted_phone}. Let me fetch your policy details...")
                ],
                "tool_calls": [
                    {
                        "name": "get_policy_summary",
                        "args": {"phone_number": extracted_phone},
                    }
                ],
                "state": {
                    **state,
                    "phone_number": extracted_phone,
                }
            }

    
    # Step 1: If we have phone number but no policy number, fetch policy
    if state.get("phone_number") and not state.get("policy_number"):
        return {
            "messages": [
                AIMessage(content="Thanks! Let me fetch your policy details using your phone number...")
            ],
            "tool_calls": [
                {
                    "name": "get_policy_summary",
                    "args": {"phone_number": state["phone_number"]},
                }
            ],
        }
    if state.get("policy_summary") and not state.get("confirmed_policy"):
        return {
            "messages": [
                AIMessage(content=f"Here are your policy details:\n\n{state['policy_summary']}")
            ],
            "updates": {
                "confirmed_policy": True
            }
        }
    # In your agent_node function, add this after handling get_policy_summary:
    if "get_policy_summary" in state:
        policy_result = state["get_policy_summary"]
        if isinstance(policy_result, dict):
            return {
                "messages": [
                    AIMessage(content=f"Here are your policy details:\n\n{policy_result.get('message')}")
                ],
                "state": {
                    **state,
                    "policy_number": policy_result.get("policy_number"),
                    "rsa": policy_result.get("rsa"),
                    "awaiting_confirmation": True  # Ask user to confirm
                }
            }       
    if state.get("Road side Assistance") is True and not state.get("towing_service"):
        return {
        "messages": [
            AIMessage(content="Your policy includes RSA. Do you need a towing service or a cab service?")
        ]
    }
    # Step 2: Handle user confirmation before raising ticket
    if state.get("awaiting_confirmation", False):
     if all(state.get(k) for k in ["accident_location", "accident_date", "accident_time"]):

        if "yes" in last_message or "confirm" in last_message:
            combined_datetime = f"{state['accident_date']} {state['accident_time']}"
            return {
            "messages": [AIMessage(content="Great, I'll raise your ticket now...")],
             "tool_calls": [
            {
                "name": "create_fnol_ticket_tool",
                "args": {
                    "phone_number": state["phone_number"],
                    "policy_number": state["policy_number"],
                    "location": state["accident_location"],
                    "accident_date_time": combined_datetime,
                },
            }
        ],
    }
        elif "no" in last_message or "change" in last_message:
            return {
                "messages": [AIMessage(content="What would you like to change?")],
                "state": {**state, "awaiting_confirmation": False},
            }
        else:
            return {
                "messages": [
                    AIMessage(content="Please confirm with 'yes' or 'no', or let me know what to change.")
                ]
            }

    # Step 3: If all required details are present, and not yet confirmed, show summary & ask for confirmation
    required_fields = [
        "phone_number", "policy_number", "accident_date",
        "accident_time", "accident_location", "accident_details"
    ]
    if all(state.get(field) for field in required_fields) and not state.get("ticket_created"):
        summary = f"""
Before we proceed, please confirm the following accident details:
-  Phone: {state['phone_number']}
-  Policy: {state['policy_number']}
-  Location: {state['accident_location']}
-  Date: {state['accident_date']}
-  Time: {state['accident_time']}
-  Description: {state['accident_details']}

Shall I go ahead and create the ticket?
"""
        
        return {
            "messages": [AIMessage(content=summary)],
            "state": {**state, "awaiting_confirmation": True},
        }

    # Step 4: If user already confirmed and all data is there, create FNOL ticket
    
    if (
        state.get("phone_number")
        and state.get("policy_number")
        and state.get("accident_location")
        and state.get("accident_date")
        and state.get("accident_time")
        and state.get("awaiting_confirmation") == True
    ):
        
        print("🎟️ [DEBUG] Creating FNOL ticket with data:")
        combined_datetime = f"{state['accident_date']} {state['accident_time']}"
        return {
    "messages": [AIMessage(content="Creating your FNOL ticket now...")],
    "tool_calls": [
        {
            "name": "create_fnol_ticket_tool",
            "args": {
                "phone_number": state["phone_number"],
                "policy_number": state["policy_number"],
                "location": state["accident_location"],
                "accident_date_time": combined_datetime,
            },
        }
    ],
}

    
    # If no tool matched, continue conversation normally
    print("🌀 [DEBUG] No matching tool or condition. Continuing conversation with LLM.")
    response = llm_with_tools.invoke(messages + [SystemMessage(content=system_prompt)])
    return {"messages": [response]}


def run_conversation():
    config = {"configurable": {"thread_id": "1"}}

    print("Starting conversation...")
    state = graph.invoke({"messages": [{"type": "human", "content": "Hi"}]}, config)

    print(f'\nAssistant: {state["messages"][-1].content}')

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ["quit", "exit"]:
            print("\nAssistant: Goodbye!")
        # Skip empty input
        if not user_input:
            print("Input cannot be empty. Please enter a valid message.")
            continue

        for event in graph.stream(
            {"messages": [HumanMessage(content=user_input)]}, config
        ):
            for value in event.values():
                if "messages" in value and value["messages"]:
                    message = value["messages"][-1]
                    if isinstance(message, AIMessage):
                        if message.content:
                            print(f"\nAssistant: {message.content}")
                        elif message.tool_calls:
                            print("\nAssistant: Processing your request...")


import requests
# ========== GRAPH ==========
builder = StateGraph(State)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    lambda state: "tools" if state.get("tool_calls") else END
)
builder.add_edge("tools", "agent")

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
#
#####################################
#FRONTEND
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import logging
from typing import Optional

app = FastAPI()
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class ChatRequest(BaseModel):
    message: str
    thread_id: str
    
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Enhanced with detailed logging"""
    print(f"\n=== Received Request ===")
    print(f"Message: {request.message}")
    print(f"Thread ID: {request.thread_id}")

    try:
        # Create LangChain message
        human_message = HumanMessage(content=request.message)
        print(f"Created HumanMessage: {human_message}")

        # Prepare graph input
        thread_id = request.thread_id or f"thread_{hash(request.message)}"
        graph_input = {
            "messages": [human_message],
            "thread_id": thread_id
        }
        print(f"Graph input: {graph_input}")

        # Invoke graph
        print("Invoking graph...")
        result = graph.invoke(
            graph_input,
            {"configurable": {"thread_id": thread_id}}
        )
        print(f"Graph result: {result}")

        # Extract response
        last_message = result["messages"][-1]
        response = {
            "response": last_message.content,
            "thread_id": thread_id
        }
        print(f"Returning response: {response}")
        return response
        
    except Exception as e:
        print(f"ERROR in chat_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
  



if __name__ == "__main__":
    run_conversation()
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)