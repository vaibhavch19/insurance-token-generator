import pdfplumber
import json
import os
import sqlite3
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(
    api_key=os.getenv('GOOGLE_GENERATIVE_API_KEY'),
    model="gemini-1.5-flash",
    temperature=0.7
)

def get_pdf_path_from_phone(phone_number):
    with sqlite3.connect("motor_insurance_policy.db") as conn:
        cursor = conn.cursor()
        query = "SELECT pdf_path FROM insurance_documents WHERE phone_number = ?"
        cursor.execute(query, (phone_number,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            raise ValueError("No document found for the given phone number.")

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

def summarize_insurance_by_phone(phone_number):
    try:
        pdf_path = get_pdf_path_from_phone(phone_number)
        policy_text = extract_text_from_pdf(pdf_path)
        prompt = f"""
        Extract the following fields from the motor insurance text and respond with valid JSON only:
        - policy_number
        - policy_type ("Comprehensive" or "Third-Party")
        - policy_start_date
        - policy_end_date
        - deductible
        - liability_amount
        - RSA (available or not)
        
        Example:
          "policy_number": "XXXXXX",
          "policy_type": "Comprehensive",
          "policy_start_date": "DD-MM-YYYY",
          "policy_end_date": "DD-MM-YYYY",
          "deductible": "Rs. XX,XX,XXX.XX",
          "liability_amount": "Rs. XX,XX,XXX.XX",
          "rsa": True or False
        
        Policy Text:
        {policy_text}
        
        Your response should just be the JSON string without any markdown formatting.
        """
        messages = [
            SystemMessage(content="You are a helpful assistant extracting insurance details."),
            HumanMessage(content=prompt)
        ]
        response = llm.invoke(messages).content.strip()
        print(f'{response = }')
        if response.startswith("```json"):
            response = response.removeprefix("```json").removesuffix("```").strip()
        data = json.loads(response)
        return data
    
    except Exception as e:
        # return {"error": str(e)}
        print(e)
    
def main():
    phone_number = input("Enter the phone number: ")
    data = summarize_insurance_by_phone(phone_number)
    print(json.dumps(data, indent=4))
    
if __name__ == '__main__':
    main()