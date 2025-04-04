from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import requests
import uvicorn 

app = FastAPI()

# Allow frontend to access backend APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
connections = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received: {data}")

            # Example processing
            if "policy" in data.lower():
                response = "Please provide your policy number to fetch details."
            else:
                response = f"Echo: {data}"

            await websocket.send_text(response)
    except WebSocketDisconnect:
        connections.remove(websocket)

@app.get("/api/policy-summary/{policy_id}")
async def get_policy_summary(policy_id: str):
    """Fetch policy summary from external API"""
    try:
        summarizer_url = f"http://policy-summarizer-url/api/summary/{policy_id}"
        response = requests.get(summarizer_url)
        return response.json()
    except Exception as e:
        return {"error": "Failed to fetch policy summary", "details": str(e)}

@app.post("/api/raise_ticket")
async def raise_ticket(data: dict):
    """Submit a ticket with policy ID and incident details"""
    try:
        policy_id = data.get("policyId")
        incident_details = data.get("incidentDetails")
        return {
            "success": True,
            "message": "ticket raised successfully",
            "policyId": policy_id,
            "incidentDetails": incident_details,
        }
    except Exception as e:
        return {"error": "Failed to submit claim", "details": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
