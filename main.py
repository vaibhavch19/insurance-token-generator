
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
    response = llm_with_tools.invoke([{'role': 'system', 'content': system_prompt}] + messages)
    return {'messages': [response]}

