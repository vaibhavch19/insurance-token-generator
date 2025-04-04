import pdfplumber
import json
import os
import sqlite3  # or use your specific database module
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.sql_database import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
# Initialize the LLM
# llm = ChatOpenAI(model_name="gpt-4o", openai_api_key="320858c52dcd4d0a87c913604e16d562")
llm = ChatGoogleGenerativeAI(
    #api_key=os.getenv('GOOGLE_GENERATIVE_API_KEY'),
    api_key="AIzaSyAs2IUf5H9I1m9GQ8flGoj0KmAAPCu5DIE",
    model="gemini-1.5-flash",
    temperature=0.7,
    max_tokens=100
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
    3. **Policy Validity**: Extract if the policy is currently valid or expired.
    4. **Deductible Amount**: The compulsory deductible amount in INR.
    5. **Liability Amount**: The third-party property damage liability amount.
    6. **Roadside Assistance(RSA) Availability**: Whether roadside assisstance(RSA) is available or not.
    7. **Other Claims Available**: Any additional claims mentioned (e.g., PA Cover, Roadside Assistance, etc.).


    Ensure the response is **valid JSON format** like this:
    ```json
    {{
      "policy_number": "XXXXXX",
      "policy_type": "Comprehensive/Third Party",
      "policy_valid": "Valid/Expired",
      "deductible": "Rs. XXXX",
      "liability_amount": "Rs. XXXX",
      "RSA": "Yes/No",
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
    response = llm(messages)
    return response.content

# 🔄 Main Execution Flow
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

