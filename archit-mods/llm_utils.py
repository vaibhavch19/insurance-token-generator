from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    api_key="AIzaSyAs2IUf5H9I1m9GQ8flGoj0KmAAPCu5DIE",
    model="gemini-1.5-flash",
    temperature=0.7,
    max_tokens=100
)

def extract_policy_info(pdf_path):
    with open(pdf_path, 'rb') as f:
        return llm("Extract key details from this policy: " + f.read().decode())