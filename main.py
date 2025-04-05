from typing import List, Dict, Optional, Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
##############################
from typing import Dict, List, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
load_dotenv()
###############
from summarizer import summarize_insurance_by_phone
import json

API_URL = "http://localhost:8000"

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
    
     # New flag to track confirmation state

# ========== LLM ==========
# llm = AzureChatOpenAI(
#     api_key=os.getenv('AZURE_OPENAI_API_KEY'),
#     api_version='2023-06-01-preview',
#     azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
#     temperature=0.7
# )
#llm = ChatOpenAI(model_name="gpt-4o", openai_api_key="320858c52dcd4d0a87c913604e16d562")
llm = ChatGoogleGenerativeAI(
    api_key="AIzaSyAs2IUf5H9I1m9GQ8flGoj0KmAAPCu5DIE",
    model="gemini-1.5-flash",
    temperature=0.7,
    max_tokens=100
)
# ========== TOOLS ==========
@tool
def fetch_policy_summary(phone_number: str) -> str:
    '''Fetch policy details using the user's phone number'''
    try:
        summary_str = summarize_insurance_by_phone(phone_number)
        summary = json.loads(summary_str)
        return f"""
Here are your policy details:

• Policy Number: {summary["policy_number"]}
• Policy Type: {summary["policy_type"]}
• Validity: {summary["policy_valid"]}
• Deductible: {summary["deductible"]}
• Liability: {summary["liability_amount"]}
• RSA: {summary["RSA"]}
• Other Claims: {", ".join(summary["other_claims"]) if "other_claims" in summary else "None"}

Please confirm if these details are correct.
"""
    except Exception as e:
        return f"❌ Error fetching policy summary: {e}"
        return {"error": str(e)}
@tool
def fetch_RSA_details(policy_number: str) -> Dict:
    '''Fetch if RSA is included in the policy'''
    response = requests.post(f'{API_URL}/fetch-rsa-details', json={'policy_number': policy_number})
    rsa_details = response.json().get('rsa_details', {}) if response.status_code == 200 else {}
    return {'rsa_details': rsa_details}
@tool
def get_policy_summary(user_summary: str) -> Dict:
    '''Fetch policy summary using phone number through summarizer.py'''
    response = requests.post(f'{API_URL}/get_policy_summary', json={'phone_number': user_summary})
    policy_summary = response.json()['policy_summary'] if response.status_code == 200 else {}
    return {'policy_summary': policy_summary}
  

# @tool
# def raise_ticket(name: str, age: int, date: str, slot: str) -> Dict:
#     '''Save ticket details'''
#     return {
#         'name': name,
#         'age': age,
#         'date': date,
         
#     }
          

@tool  
def create_fnol(ticket_id: str, ftp_link: str, report_link: str, ticket_date_time: str) -> Dict:
    '''Fetch user summary of accident with pictures or videos on the FTP link'''
    return {
        'ticket_id': ticket_id,
        'ftp_link':ftp_link,
        'report_link': report_link,
        'ticket_date_time': True,
        'accident_summary': True,
    }

@tool
def raise_ticket(state: State) -> Dict:
    '''Book an appointment with all collected details'''
    if not state.get('ticket_created', False):
        return {'error': 'Ticket not created yet'}
    if not state.get('awaiting_confirmation', False):
        return {'error': 'Confirmation not received'}
    if not state.get('accident_summary', False):
        return {'error': 'Accident summary not provided'}
    
    if not state.get('accident_location', False):
        return {'error': 'Accident location not provided'}
    if not state.get('accident_date', False):
        return {'error': 'Accident date not provided'}
    if not state.get('accident_time', False):
        return {'error': 'Accident time not provided'}
    if not state.get('accident_details', False):
        return {'error': 'Accident details not provided'}
    
    
    
    response = requests.post(f'{API_URL}/ticket_raising', json={
        'fetch_policy' : state['fetch_policy'],
        'policy': state['policy'],
        'rsa': state['rsa'],
        'accident_date': state['accident_date'],
        'accident_time': state['accident_time'],
        'accident_location': state['accident_location'],
        'accident_details': state['accident_details'],
        'towing_service': state['towing_service'],
        'cab_service': state['cab_service'],
        'ftp_link': state['ftp_link'],
        'scene_recreation': state['scene_recreation'],
        'accident_summary': state['accident_summary'],
        'ticket_id': state['ticket_id'],
        'ticket_created': state['ticket_created'],
        'awaiting_confirmation': state['awaiting_confirmation'],

        
    })
    result = response.json() if response.status_code == 200 else {'error': 'Booking failed'}
    return result

tools = [
    fetch_policy_summary,
    fetch_RSA_details, 
    raise_ticket,
    create_fnol
]

llm_with_tools = llm.bind_tools(tools)
import re

# Helper function to detect phone numbers
def extract_phone_number(text: str) -> Optional[str]:
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

############################
def agent_node(state: State) -> Dict:
    messages = state['messages']
    
    # Initial greeting
    if not messages:
        return {
            'messages': [AIMessage(content='Hello! I am your car insurance agent. How may I assist you today?')]
        }
    phone_number = state.get("phone_number")
    policy_number = state.get("policy_number")
    location = state.get("accident_location")
    accident_date = state.get("accident_date")
    accident_time = state.get("accident_time")

    # Combine date and time safely
    accident_date_time = f"{accident_date} {accident_time}" if accident_date and accident_time else None

    # Only call create_fnol_ticket if all required fields are available
    if phone_number and policy_number and location and accident_date_time:
        fnol_response = create_fnol_ticket(phone_number, policy_number, location, accident_date_time)

        if "ftp_link" in fnol_response:
            ftp_link = fnol_response["ftp_link"]
            return {
                'messages': [AIMessage(content=f'''
    ✅ Your FNOL ticket has been created!

    📎 Please upload accident photos/videos here: {ftp_link}

    Do you need anything else?''')],
                'ftp_link': ftp_link,
                'ticket_created': True,
                'ticket_id': fnol_response.get('ticket_id', ''),
                'accident_summary': True
            }
        else:
            return {
                'messages': [AIMessage(content="❌ There was an issue creating your FNOL ticket. Please try again later.")]
            }

    # System prompt for LLM
    system_prompt = f'''
   You are a helpful insurance assistant helping users file accident claims.
   Start by greeting the user.
   When the user mentions an accident or claim, politely ask for their phone number so you can fetch their policy details.
   Once phone number is provided, call the `fetch_policy_summary` tool to retrieve policy info. Wait for confirmation from user.
   If RSA is included in the policy, ask the user if they require towing or cab services.
    
    - ask for users a nearby location where the accident happened.
    - send user a FTP link for a summary of accident with pictures or videos.
    - create a ticket and send it to the user.
    
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
    Scene Recreation: {state.get('scene_recreation', 'Not provided')}
    Accident Summary: {state.get('accident_summary', 'Not provided')}
    Ticket Created: {state.get('ticket_created', False)}
    Ticket ID: {state.get('ticket_id', 'Not provided')}
    Awaiting Confirmation: {state.get('awaiting_confirmation', False)}

    Rules:
    1. Collect all required details (mobile number, policy number, RSA if needed, date, time) before creating a ticket. In fact, you can start by capturing the name and phone number and policy number.
    2. After collecting all details via save_accident_details, present the scene recreation to the user for confirmation.
    3. Only call create_ticket after explicit user confirmation (e.g., 'yes' or 'confirm').
    4. If user says 'no' or requests changes during confirmation, ask what to modify.
    5. After successful booking, ask if they need more help.
    6. If asked about unrelated topics, politely refuse and redirect to ticket raising.
    Current date: {datetime.now().strftime('%Y-%m-%d')}
    '''

    # Handle tickt raising response
    last_message = messages[-1].content.lower() if messages and isinstance(messages[-1], HumanMessage) else ''
    if state.get('awaiting_confirmation', False):
        if 'yes' in last_message or 'confirm' in last_message:
            return {
                'messages': [AIMessage(content='Great, I\'ll raise your ticket now...')],
                'tool_calls': [{'name': 'raise_ticket', 'args': {'state': state}}]
            }
        elif 'no' in last_message or 'change' in last_message:
            return {
                'messages': [AIMessage(content='What would you like to change?')],
                'awaiting_confirmation': False
            }
        else:
            return {
                'messages': [AIMessage(content='Please confirm with \'yes\' or \'no\', or let me know what to change.')]
            }

    response = llm_with_tools.invoke(messages + [SystemMessage(content=system_prompt)])
    return {'messages': [response]}

##########################################

#############################
def run_conversation():
    config = {'configurable': {'thread_id': '1'}}
    
    print('Starting conversation...')
    state = graph.invoke({'messages': []}, config)
    print(f'\nAssistant: {state["messages"][-1].content}')
    
    while True:
        user_input = input('\nYou: ').strip()
        if user_input.lower() in ['quit', 'exit']:
            print('\nAssistant: Goodbye!')
          # Skip empty input
        if not user_input:
            print("Input cannot be empty. Please enter a valid message.")
            continue


            
        
        for event in graph.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config
        ):
            for value in event.values():
                if 'messages' in value and value['messages']:
                    message = value['messages'][-1]
                    if isinstance(message, AIMessage):
                        if message.content:
                            print(f'\nAssistant: {message.content}')
                        elif message.tool_calls:
                            print('\nAssistant: Processing your request...')

import requests

def create_fnol_ticket(phone_number, policy_number, location, accident_date_time):
    fnol_data = {
        "phone_number": phone_number,
        "policy_number": policy_number,
        "location": location,
        "accident_date_time": accident_date_time
    }

    try:
        response = requests.post("http://localhost:5000/create_fnol/", json=fnol_data)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to create FNOL entry", "details": response.text}
    except Exception as e:
        return {"error": str(e)}

# ========== GRAPH ==========
builder = StateGraph(State)
builder.add_node('agent', agent_node)
builder.add_node('tools', ToolNode(tools))

builder.add_edge(START, 'agent')
builder.add_conditional_edges('agent', tools_condition)
builder.add_edge('tools', 'agent')
builder.add_edge('agent', END)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)


if __name__ == '__main__':
    run_conversation()





