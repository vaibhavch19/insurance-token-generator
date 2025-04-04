import pdfplumber
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# Load OpenAI LLM via LangChain
llm = ChatOpenAI(model_name="gpt-4o", openai_api_key="320858c52dcd4d0a87c913604e16d562")

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

# Function to ask LLM for structured extraction
def extract_insurance_details_llm(text):
    prompt = f"""
    Extract the following details from the given motor insurance policy text and return the result in JSON format:

    1. **Policy Number**: The unique number assigned to the policy.
    2. **Policy Type**: Whether it is "Comprehensive" or "Third Party".
    3. **Policy Validity**: Extract if the policy is currently valid or expired.
    4. **Deductible Amount**: The compulsory deductible amount in INR.
    5. **Liability Amount**: The third-party property damage liability amount.
    6. **Other Claims Available**: Any additional claims mentioned (e.g., PA Cover, Roadside Assistance, etc.).

    Ensure the response is **valid JSON format** like this:
    ```json
    {{
      "policy_number": "XXXXXX",
      "policy_type": "Comprehensive/Third Party",
      "policy_valid": "Valid/Expired",
      "deductible": "Rs. XXXX",
      "liability_amount": "Rs. XXXX",
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

# **Main Execution**
pdf_path = "Vehicle_Insurance_Certificate_in_India.pdf"

# Extract text
policy_text = extract_text_from_pdf(pdf_path)

# Get extracted data from LLM
insurance_summary = extract_insurance_details_llm(policy_text)

# Print extracted details
print(insurance_summary)
