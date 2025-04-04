from typing import List, Dict, Optional, Annotated
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI

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
llm = ChatOpenAI(model_name="gpt-4o", openai_api_key="320858c52dcd4d0a87c913604e16d562")

# ========== TOOLS ==========
 
@tool
def fetch_policy(policy_number: str) -> Dict:
    '''Fetch policy based on policy number'''
    response = requests.post(f'{API_URL}/fetch-policy-number', json={'tests': tests})
    policy_number = response.json()['policy_number'] if response.status_code == 200 else ''
    return {'policy_number': policy_number}
    
@tool
def fetch_RSA_details(policy_number: str) -> Dict:
    '''Fetch if RSA is included in the policy'''
    response = requests.post(f'{API_URL}/fetch-rsa-details', json={'location': location, 'tests': tests})
    rsa_details = response.json()['rsa_details'] if response.status_code == 200 else {}
    return {'rsa_details': rsa_details}
   
@tool
def fetch_user_summary(user_summary: str) -> Dict:
    '''Fetch user summary of accident with pictures or videos on a FTP link'''
    response = requests.post(f'{API_URL}/fetch-accident-summary', json={'tests': tests})
    summary = response.json()['accident_summary'] if response.status_code == 200 else {}
    return {'accident_summary': summary}
    

@tool
def save_ticket_details(name: str, age: int, date: str, slot: str) -> Dict:
    '''Save ticket details'''
    return {
        'name': name,
        'date':date,
        'RSA details': True,
        'user_summary': True,
        'awaiting_confirmation': True
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
    fetch_policy,
    fetch_RSA_details, 
    fetch_user_summary,
    save_ticket_details,
    raise_ticket
]

llm_with_tools = llm.bind_tools(tools)


############################
def agent_node(state: State) -> Dict:
    messages = state['messages']
    
    # Initial greeting
    if not messages:
        return {
            'messages': [AIMessage(content='Hello! I am your car insurance agent. How may I assist you today?')]
        }

    # System prompt for LLM
    system_prompt = f'''
    You are a helpful assistant for a car insurance company, assisting customers with raising First notice of loss tickets.
    Use the provided tools to:
    - Fetch details based on phone number/policy number.
    - Ask the accident date and time.
    - Check if RSA (Road Side Assistance) is included in the policy.
    - Ask user for car towing and cab service if RSA is included.
    - ask for users location (a google map link) and send it to ##DATABASE##.
    - send user a FTP link for a summary of accident with pictures or videos.
    - make a scene recreation for the accident and check it with the user.
    - when the user confirms, create a ticket and send it to the database.
    
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

    # Invoke LLM with current conversation and state
    # response = llm_with_tools.invoke([{'role': 'system', 'content': system_prompt}] + messages)
    response = asyncio.run(send_message_to_backend(messages[-1].content))

    return {'messages': [response]}

##########################################
import asyncio
import websockets
import json

WEBSOCKET_URL = "ws://localhost:8000/ws"  # Ensure it matches FastAPI WebSocket route

async def send_message_to_backend(message):
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        await websocket.send(message)
        response = await websocket.recv()
        return response

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


            break
        
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





