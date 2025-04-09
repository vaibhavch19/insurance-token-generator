from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class State(TypedDict):
    mobile_number: str
    policy_details: dict
    rsa_available: bool
    accident_details: str
    ticket_id: str
    upload_link: str
    report_link: str
    messages: Annotated[list, operator.add]

def fetch_policy(state):
    from db_handler import get_policy_details
    policy = get_policy_details(state["mobile_number"])
    return {"policy_details": policy, "rsa_available": policy["rsa_available"]}

def check_rsa(state):
    if state["rsa_available"]:
        return {"messages": ["Is tow assistance required? What about cab assistance?"]}
    return {"messages": ["No RSA available. Please provide accident details."]}

def raise_ticket(state):
    from db_handler import create_ticket
    ticket_id = create_ticket(state["mobile_number"], state["accident_details"])
    upload_link = f"http://localhost:5000/upload_files/{ticket_id}"
    return {"ticket_id": ticket_id, "upload_link": upload_link, "messages": [f"Ticket {ticket_id} raised. Upload files here: {upload_link}"]}

def generate_report(state):
    from report_generator import create_report
    report_link = create_report(state["ticket_id"])
    return {"report_link": report_link, "messages": ["Here’s your report: " + report_link]}

def end_conversation(state):
    return {"messages": ["Anything else I can help you with?"]}

graph = StateGraph(State)
graph.add_node("fetch_policy", fetch_policy)
graph.add_node("check_rsa", check_rsa)
graph.add_node("raise_ticket", raise_ticket)
graph.add_node("generate_report", generate_report)
graph.add_node("end_conversation", end_conversation)

graph.set_entry_point("fetch_policy")
graph.add_edge("fetch_policy", "check_rsa")
graph.add_conditional_edges("check_rsa", lambda state: "raise_ticket" if state["accident_details"] else "check_rsa")
graph.add_edge("raise_ticket", "generate_report")
graph.add_edge("generate_report", "end_conversation")
graph.add_edge("end_conversation", END)

app = graph.compile()

def run_agent_workflow(mobile_number):
    initial_state = {"mobile_number": mobile_number, "messages": []}
    result = app.invoke(initial_state)
    return result