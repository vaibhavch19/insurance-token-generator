import requests

# URL of your FastAPI endpoint
url = "http://localhost:5050/create_fnol/"

# Sample FNOL payload data
payload = {
    "phone_number": "9876543210",
    "policy_number": "POL1234567",
    "location": "Delhi",
    "accident_date_time": "2025-04-14 10:30:00"
}

# Send the POST request
response = requests.post(url, json=payload)

# Print response status and data
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
