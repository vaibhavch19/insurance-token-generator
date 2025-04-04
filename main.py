from typing import List, Dict, Optional, Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from datetime import datetime
import os
import json
from dotenv import load_dotenv
import summarizer  # 🔄 UPDATED: Import summarizer.py

load_dotenv()
API_URL = "http://localhost:8000"

# ========== STATE ==========
class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
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

# ========== LLM ==========
llm = ChatGoogleGenerativeAI(
    api_key=os.getenv('GOOGLE_GENERATIVE_API_KEY'),
    model="gemini-1.5-flash",
    temperature=0.7,
    max_tokens=100
)

# ========== TOOLS ==========
@tool
def fetch_policy_details(phone_number: str) -> Dict:
    '''Fetch policy details using the given phone number.'''
    policy_details = summarizer.summarize_insurance_by_phone(phone_number)  # 🔄 UPDATED: Fetch from summarizer.py
    try:
        policy_json = json.loads(policy_details)  # Ensure it's valid JSON
        return policy_json
    except json.JSONDecodeError:
        return {"error": "Could not fetch policy details."}

tools = [fetch_policy_details]
llm_with_tools = llm.bind_tools(tools)

############################
def agent_node(state: State) -> Dict:
    messages = state['messages']

    # 🔄 UPDATED: If phone number is not collected, ask for it first
    if not state.get('phone_number'):
        return {'messages': [AIMessage(content="Please provide your mobile number to fetch your policy details.")]}

    # 🔄 UPDATED: If phone number is collected but policy not fetched, fetch it
    if state.get('phone_number') and not state.get('policy_number'):
        return {
            'messages': [AIMessage(content="Fetching your policy details...")],
            'tool_calls': [{'name': 'fetch_policy_details', 'args': {'phone_number': state['phone_number']}}]
        }

    # If we have policy details, continue normal conversation
    last_message = messages[-1].content.lower() if messages and isinstance(messages[-1], HumanMessage) else ''

    return {'messages': [AIMessage(content="How may I assist you today regarding your policy?")]}

############################
def run_conversation():
    config = {'configurable': {'thread_id': '1'}}
    
    print('Starting conversation...')
    state = {'messages': [], 'phone_number': None, 'policy_number': None}

    while True:
        user_input = input('\nYou: ').strip()
        if user_input.lower() in ['quit', 'exit']:
            print('\nAssistant: Goodbye!')
            break

        # 🔄 UPDATED: If phone number is missing, store it and trigger policy fetch
        if not state['phone_number']:
            state['phone_number'] = user_input
            response = agent_node(state)
            state['messages'].append(HumanMessage(content=user_input))
            print(f"\nAssistant: {response['messages'][-1].content}")
            continue

        # 🔄 UPDATED: Handle normal conversation after policy details are fetched
        state['messages'].append(HumanMessage(content=user_input))
        response = agent_node(state)

        if 'tool_calls' in response:
            tool_name = response['tool_calls'][0]['name']
            tool_args = response['tool_calls'][0]['args']
            
            if tool_name == "fetch_policy_details":
                policy_data = fetch_policy_details(tool_args["phone_number"])
                
                if "error" in policy_data:
                    print("\nAssistant: Unable to fetch policy details. Please try again.")
                else:
                    state.update(policy_data)  # Store policy details
                    print("\nAssistant: Policy details retrieved. How may I assist you?")

            continue

        print(f"\nAssistant: {response['messages'][-1].content}")

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

######################
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chatbot")
async def chatbot_response(request: ChatRequest):
    """Processes chatbot conversation"""
    user_message = request.message
    bot_response = f"Bot received: {user_message}"  
    return {"response": bot_response}

if __name__ == '__main__':
    run_conversation()
