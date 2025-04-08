import requests

url = "http://localhost:5050/create_fnol/"
payload = {
    "phone_number": "9876543210",
    "policy_number": "POLICY123",
    "location": "Mumbai",
    "accident_date_time": "2025-04-07 10:30:00"
}

response = requests.post(url, json=payload)

print("Status Code:", response.status_code)
print("Response JSON:", response.json())