import streamlit as st
import requests

st.title("FNOL Chatbot")

API_URL = 'http://0.0.0.0:8000'

# Store messages in session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display conversation
for msg in st.session_state["messages"]:
    alignment = "user" if msg["sender"] == "user" else "bot"
    with st.chat_message(alignment):
        st.write(msg["text"])

# User input field
user_input = st.text_input("Type a message", key="user_input")

# Send message when "Send" button is clicked
if st.button("Send"):
    if not user_input.strip():
        st.warning("Message cannot be empty. Please enter a valid message.")
    else:
        st.session_state["messages"].append({"text": user_input, "sender": "user"})

        try:
            # Check if input is a phone number or policy number
            if user_input.replace(" ", "").isalnum():  # Allows numbers and letters
                response = requests.get(f'{API_URL}/api/policy-summary/{user_input}')
            else:
                response = requests.post(f'{API_URL}/chat', json={"message": user_input})

            bot_response = response.json().get("response", str(response.text))
            st.session_state["messages"].append({"text": bot_response, "sender": "bot"})

        except Exception as e:
            st.error(f"Error: {e}")

        st.rerun()  # Refresh to show new messages





# import streamlit as st
# import requests
# # import websocket
# # import threading

# st.title("FNOL Chatbot")

# # WebSocket server URL (ensure backend is running)
# # WS_URL = "ws://localhost:8000/ws"
# API_URL = 'http://0.0.0.0:8000'

# # Store messages in session state
# if "messages" not in st.session_state:
#     st.session_state["messages"] = []

# # # WebSocket message handler
# # def on_message(ws, message):
# #     st.session_state["messages"].append({"text": message, "sender": "bot"})
# #     st.rerun()

# # # WebSocket connection handler
# # def on_open(ws):
# #     st.session_state["ws"] = ws

# # # Start WebSocket connection thread
# # def start_websocket():
# #     ws = websocket.WebSocketApp(
# #         WS_URL,
# #         on_message=on_message,
# #         on_open=on_open
# #     )
# #     ws.run_forever()

# # Initialize WebSocket connection once
# # if "ws_thread" not in st.session_state:
# #     st.session_state["ws_thread"] = threading.Thread(target=start_websocket, daemon=True)
# #     st.session_state["ws_thread"].start()

# # Display conversation
# for msg in st.session_state["messages"]:
#     alignment = "user" if msg["sender"] == "user" else "bot"
#     with st.chat_message(alignment):
#         st.write(msg["text"])

# # User input and send message
# if st.button("Send"):
#     if not user_input.strip():
#         st.warning("Message cannot be empty. Please enter a valid message.")
#     else:
#         st.session_state["messages"].append({"text": user_input, "sender": "user"})
        
#         try:
#             response = requests.post(f'{API_URL}/chat', json={"message": user_input})
#             bot_response = response.json().get("response", "Sorry, something went wrong.")
#             st.session_state["messages"].append({"text": bot_response, "sender": "bot"})
#         except Exception as e:
#             st.error(f"Error: {e}")

#         st.rerun()

# user_input = st.text_input("Type a message", key="user_input")
# if st.button("Send") and user_input:
#     st.session_state["messages"].append({"text": user_input, "sender": "user"})
    
#     try:
#         response = requests.get(f'{API_URL}/api/policy-summary/{user_input}')
#         st.session_state["messages"].append({"text": str(response.text), "sender": "bot"})
#     except Exception as e:
#         st.error(f"Error: {e}")

#     st.rerun()  # Updated from st.experimental_rerun()
