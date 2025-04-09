from flask import Flask, request, jsonify
from flask_cors import CORS
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
import os
import json
import logging
from config import FLASK_HOST, FLASK_PORT, UPLOAD_DIR, REPORT_DIR
from db_handler import get_policy_details, create_ticket
from werkzeug.utils import secure_filename
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Enable debug logging
app.logger.setLevel(logging.DEBUG)

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(
    api_key="AIzaSyAs2IUf5H9I1m9GQ8flGoj0KmAAPCu5DIE",
    model="gemini-1.5-flash",
    temperature=0.7,
    max_tokens=100
)

# Prompt templates
rsa_prompt = PromptTemplate(
    input_variables=["context"],
    template="Given this context: {context}, ask the user in a friendly, natural way if they need tow assistance or a cab, expecting a Yes/No answer."
)
input_prompt = PromptTemplate(
    input_variables=["step", "prev_message"],
    template="For step '{step}' and previous message '{prev_message}', politely ask the user for input in a conversational tone."
)
parse_prompt = PromptTemplate(
    input_variables=["user_input", "step"],
    template="""
    Interpret this user input: '{user_input}' for step '{step}'. Return a valid JSON string with thw following keys:
    
    "response": "next message"
    "proceed": true/false
    
    with 'response' (next message) and 'proceed' (True/False). If unclear, set 'proceed' to false and ask for clarification in 'response'. Ensure JSON is properly formatted.
    """
)
report_prompt = PromptTemplate(
    input_variables=["accident_details", "ticket_id"],
    template="Create a detailed claim summary and scene recreation for ticket {ticket_id} based on accident details: {accident_details}. Format as a concise report."
)

class State(TypedDict):
    mobile_number: str
    policy_details: dict
    rsa_available: bool
    accident_details: str
    ticket_id: str
    upload_link: str
    report_link: str
    messages: Annotated[list, operator.add]
    user_input: str
    step: str

def fetch_policy(state):
    try:
        policy = get_policy_details(state["mobile_number"])
        updated_state = state.copy()
        updated_state.update({
            "policy_details": policy,
            "rsa_available": policy["rsa_available"],
            "messages": ["Great, I found your policy! Let’s check if RSA is available..."],
            "step": "check_rsa"
        })
        app.logger.debug(f"fetch_policy state: {updated_state}")
        return updated_state
    except ValueError as e:
        updated_state = state.copy()
        updated_state.update({
            "messages": [f"Sorry, I couldn’t find a policy for {state['mobile_number']}. Please check the number."],
            "step": "end"
        })
        app.logger.debug(f"fetch_policy state (error): {updated_state}")
        return updated_state

def check_rsa(state):
    updated_state = state.copy()
    if state["rsa_available"]:
        message = llm.invoke(rsa_prompt.format(context="User has roadside assistance available")).content
        updated_state.update({"messages": [message], "step": "handle_rsa_response"})
    else:
        updated_state.update({
            "messages": ["It seems RSA isn’t available for your policy. Could you tell me about the accident?"],
            "step": "raise_ticket"
        })
    app.logger.debug(f"check_rsa state: {updated_state}")
    return updated_state

def handle_rsa_response(state):
    user_input = state["user_input"].strip()
    updated_state = state.copy()
    
    if not user_input:
        message = llm.invoke(input_prompt.format(step="handle_rsa_response", prev_message=state["messages"][-1])).content
        updated_state.update({"messages": [message], "step": "handle_rsa_response"})
        app.logger.debug(f"handle_rsa_response state (no input): {updated_state}")
        return updated_state
    
    prompt_text = parse_prompt.format(user_input=user_input, step="handle_rsa_response")
    app.logger.debug(f"Prompt sent to Gemini: {prompt_text}")
    parse_result = llm.invoke(prompt_text).content
    app.logger.debug(f"Raw Gemini parse result: {parse_result}")
    
    try:
        result = json.loads(parse_result)
        if "response" not in result or "proceed" not in result:
            app.logger.error(f"Invalid JSON from Gemini: missing 'response' or 'proceed' in {parse_result}")
            raise KeyError("Missing 'response' or 'proceed' in Gemini output")
        if not result["proceed"]:
            updated_state.update({"messages": [result["response"]], "step": "handle_rsa_response"})
        elif "yes" in user_input.lower():
            updated_state.update({
                "messages": ["Alright, I’ll arrange tow or cab assistance. Now, what happened in the accident?"],
                "step": "raise_ticket"
            })
        else:
            updated_state.update({
                "messages": ["Okay, no assistance needed then. Please describe the accident."],
                "step": "raise_ticket"
            })
    except json.JSONDecodeError as e:
        app.logger.error(f"Error parsing RSA response as JSON: {e}, raw result: {parse_result}")
        if "yes" in user_input.lower():
            updated_state.update({
                "messages": ["Alright, I’ll arrange tow or cab assistance. Now, what happened in the accident?"],
                "step": "raise_ticket"
            })
        elif "no" in user_input.lower():
            updated_state.update({
                "messages": ["Okay, no assistance needed then. Please describe the accident."],
                "step": "raise_ticket"
            })
        else:
            updated_state.update({
                "messages": ["I didn’t quite catch that. Could you say Yes or No to tow/cab assistance?"],
                "step": "handle_rsa_response"
            })
    except Exception as e:
        app.logger.error(f"Unexpected error parsing RSA response: {e}, raw result: {parse_result}")
        updated_state.update({
            "messages": ["Something went wrong. Could you say Yes or No to tow/cab assistance?"],
            "step": "handle_rsa_response"
        })
    app.logger.debug(f"handle_rsa_response state: {updated_state}")
    return updated_state

def raise_ticket(state):
    user_input = state["user_input"].strip()
    updated_state = state.copy()
    
    if not user_input:
        message = llm.invoke(input_prompt.format(step="raise_ticket", prev_message=state["messages"][-1])).content
        updated_state.update({"messages": [message], "step": "raise_ticket"})
        app.logger.debug(f"raise_ticket state (no input): {updated_state}")
        return updated_state
    
    ticket_id = create_ticket(state["mobile_number"], user_input)
    upload_link = f"http://{FLASK_HOST}:{FLASK_PORT}/upload/{ticket_id}"
    updated_state.update({
        "ticket_id": ticket_id,
        "upload_link": upload_link,
        "accident_details": user_input,
        "messages": [f"Ticket #{ticket_id} is raised! You can upload photos or more details here: {upload_link}"],
        "step": "generate_report"
    })
    app.logger.debug(f"raise_ticket state: {updated_state}")
    return updated_state

def generate_report(state):
    updated_state = state.copy()
    if "ticket_id" not in state or not state["ticket_id"]:
        updated_state.update({
            "messages": ["Something went wrong—no ticket ID yet. Let’s try that again."],
            "step": "raise_ticket"
        })
        app.logger.debug(f"generate_report state (no ticket_id): {updated_state}")
        return updated_state
    
    ticket_id = state["ticket_id"]
    accident_details = state["accident_details"]
    report_text = llm.invoke(report_prompt.format(accident_details=accident_details, ticket_id=ticket_id)).content
    report_path = f"{REPORT_DIR}/{ticket_id}_report.txt"
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report_text)
    report_link = f"http://{FLASK_HOST}:{FLASK_PORT}/static/reports/{ticket_id}_report.txt"
    updated_state.update({
        "report_link": report_link,
        "messages": [f"Your report is ready: {report_link}"],
        "step": "end_conversation"
    })
    app.logger.debug(f"generate_report state: {updated_state}")
    return updated_state

def end_conversation(state):
    updated_state = state.copy()
    updated_state.update({"messages": ["Is there anything else I can assist you with today?"], "step": "end"})
    app.logger.debug(f"end_conversation state: {updated_state}")
    return updated_state

node_functions = {
    "fetch_policy": fetch_policy,
    "check_rsa": check_rsa,
    "handle_rsa_response": handle_rsa_response,
    "raise_ticket": raise_ticket,
    "generate_report": generate_report,
    "end_conversation": end_conversation
}

graph = StateGraph(State)
for name, func in node_functions.items():
    graph.add_node(name, func)
graph.set_entry_point("fetch_policy")
graph.add_edge("fetch_policy", "check_rsa")
graph.add_edge("check_rsa", "handle_rsa_response")
graph.add_edge("handle_rsa_response", "raise_ticket")
graph.add_edge("raise_ticket", "generate_report")
graph.add_edge("generate_report", "end_conversation")
graph.add_edge("end_conversation", END)

agent = graph.compile()

def run_single_step(state, step):
    if step not in node_functions:
        raise ValueError(f"Invalid step: {step}")
    return node_functions[step](state)

@app.route('/start', methods=['POST'])
def start_conversation():
    try:
        data = request.json
        if not data or "mobile_number" not in data:
            return jsonify({"messages": ["Error: Missing mobile_number"], "state": {}}), 400
        mobile_number = data["mobile_number"]
        state = {"mobile_number": mobile_number, "messages": [], "user_input": "", "step": "fetch_policy"}
        result = run_single_step(state, "fetch_policy")
        result = run_single_step(result, "check_rsa")
        return jsonify({"messages": result["messages"], "state": result})
    except Exception as e:
        app.logger.error(f"Error in /start: {str(e)}")
        return jsonify({"messages": [f"Server error: {str(e)}"], "state": {}}), 500

@app.route('/respond', methods=['POST'])
def respond():
    try:
        data = request.json
        if not data or "state" not in data:
            return jsonify({"messages": ["Error: Missing state"], "state": {}}), 400
        state = data["state"]
        user_input = data.get("user_input", "").strip()
        state["user_input"] = user_input
        
        current_step = state.get("step", "fetch_policy")
        if current_step == "end":
            return jsonify({"messages": ["Conversation ended."], "state": state})
        
        result = run_single_step(state, current_step)
        return jsonify({"messages": result["messages"], "state": result})
    except Exception as e:
        app.logger.error(f"Error in /respond: {str(e)}")
        return jsonify({"messages": [f"Server error: {str(e)}"], "state": state}), 500

@app.route('/upload/<ticket_id>', methods=['POST'])
def upload_files(ticket_id):
    try:
        os.makedirs(f"{UPLOAD_DIR}/{ticket_id}", exist_ok=True)
        files = request.files.getlist("files")
        uploaded = []
        for file in files:
            filename = secure_filename(file.filename)
            file.save(os.path.join(f"{UPLOAD_DIR}/{ticket_id}", filename))
            uploaded.append(filename)
        return jsonify({"message": f"Uploaded {len(uploaded)} files for ticket #{ticket_id}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/static/<path:path>')
def serve_static(path):
    return app.send_static_file(path)

if __name__ == "__main__":
    from db_handler import init_db
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    init_db()
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)