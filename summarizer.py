import pdfplumber
import sqlite3  # or use your specific database module
from langchain_openai import AzureChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

# Initialize the LLM
llm = AzureChatOpenAI(
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    api_version='2023-06-01-preview',
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    temperature=0.7
)

# Connect to SQL database (replace with your URI if not SQLite)
db = SQLDatabase.from_uri("sqlite:///motor_insurance_policy.db")

# Function to fetch PDF path using phone number
def get_pdf_path_from_phone(phone_number):
    # Direct SQL query
    with sqlite3.connect("motor_insurance_policy.db") as conn:
        cursor = conn.cursor()
        query = "SELECT pdf_path FROM insurance_documents WHERE phone_number = ?"
        cursor.execute(query, (phone_number,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            raise ValueError("No document found for the given phone number.")

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

# Extract insurance summary using LLM
def extract_insurance_details_llm(text):
    prompt = f"""
    Extract the following details from the given motor insurance policy text and return the result in JSON format:

    1. **Policy Number**: The unique number assigned to the policy.
    2. **Policy Type**: Whether it is "Comprehensive" or "Third Party".
    3. **Policy Start Date**: Date from which the policy is valid.
    4. **Policy Expiry Date**: Date till which the policy is valid (typically a year away from policy start date).
    5. **Deductible Amount**: The compulsory deductible amount in INR.
    6. **Vehicle Insured Declared Value (IDV)**: The amount for which the vehicle is covered.
    7. **Road-side Assistance (RSA) Available**: Whether RSA is included in the policy.
    8. **Other Claims Available**: Any additional claims mentioned (e.g., PA Cover, Roadside Assistance, etc.).

    Ensure the response is **valid JSON format** like this:
    ```json
    {{
      "policy_number": "XXXXXX",
      "policy_type": "Comprehensive/Third Party",
      "policy_start_date": "DD-MM-YYYY",
      "policy_end_date": "DD-MM-YYYY",
      "deductible": "Rs. XXXX",
      "idv": "Rs. XXXX",
      "rsa": true/false,
      "other_claims": ["Claim 1", "Claim 2"]
    }}
    ```

    Motor Insurance Policy Text:
    {text}
    """
    messages = [
        SystemMessage(content="You are an expert in document processing and data extraction."),
        HumanMessage(content=prompt)
    ]
    response = llm.invoke(messages)
    return response.content

def summarize_insurance_by_phone(phone_number):
    try:
        pdf_path = get_pdf_path_from_phone(phone_number)
        policy_text = extract_text_from_pdf(pdf_path)
        summary = extract_insurance_details_llm(policy_text)
        return summary
    except Exception as e:
        return str(e)

# Example usage:
# phone = input("Enter client phone number: ")
# print(summarize_insurance_by_phone(phone))

