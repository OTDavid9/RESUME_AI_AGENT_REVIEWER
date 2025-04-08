import streamlit as st
import os
from google import genai
from google.genai import types
from typing import List, Dict
import textract
from dotenv import load_dotenv
import io # Needed for handling uploaded file bytes
import tempfile # Needed to save uploaded file temporarily for textract

# --- Configuration and Setup ---
load_dotenv()
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure Streamlit page
st.set_page_config(
    page_title="Resume AI Assistant",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Resume AI Assistant")
st.caption("Upload your resume and chat about it!")


# --- Core Logic (Adapted from your code) ---
@st.cache_data(show_spinner="Extracting text from resume...") # Cache the result
def extract_text_from_file(uploaded_file):
    """Extracts text from an uploaded file object."""
    try:
        # textract needs a filepath, so save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            filepath = tmp_file.name

        # Process the temporary file
        text_bytes = textract.process(filepath)
        text = text_bytes.decode("utf-8")
        os.remove(filepath) # Clean up the temporary file
        return text
    except Exception as e:
        st.error(f"Failed to extract text: {e}")
        # Try decoding directly for plain text as a fallback
        try:
            return uploaded_file.getvalue().decode("utf-8")
        except Exception:
            st.error("Could not decode file content as UTF-8 either.")
            return None # Indicate failure

# We don't need the review_resume function directly as a *tool* here.
# Instead, we'll inject the resume context into the general chat prompt.

# Initialize Gemini Model (using cache resource for efficiency)
@st.cache_resource
def get_gemini_model():
    """Initializes and returns the Gemini model client."""
    # Note: Adjust model name if needed, e.g., "gemini-1.5-pro-latest"
    # Using "gemini-pro" as a generally available stable model
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

model = get_gemini_model()

# --- Streamlit Session State Initialization ---

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize resume text storage
if "resume_text" not in st.session_state:
    st.session_state.resume_text = None

if "resume_uploaded" not in st.session_state:
    st.session_state.resume_uploaded = False

# --- Sidebar for File Upload ---

with st.sidebar:
    st.header("Upload Resume")
    uploaded_file = st.file_uploader(
        "Choose a file (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=False
    )

    if uploaded_file is not None:
        # Process the file only once or if a new file is uploaded
        if not st.session_state.resume_uploaded or st.session_state.get("current_file_name") != uploaded_file.name:
            extracted_text = extract_text_from_file(uploaded_file)
            if extracted_text:
                st.session_state.resume_text = extracted_text
                st.session_state.resume_uploaded = True
                st.session_state.current_file_name = uploaded_file.name # Track the current file
                st.success("✅ Resume processed successfully!")
                # Optionally add a system message to the chat
                # st.session_state.messages.append({"role": "assistant", "content": "I have received and processed your resume. How can I help you with it?"})
            else:
                st.error("❌ Failed to process the resume file.")
                st.session_state.resume_text = None
                st.session_state.resume_uploaded = False
                st.session_state.current_file_name = None

    elif st.session_state.resume_uploaded:
        # If a file was previously uploaded but now none is selected
        st.info("Resume was previously uploaded. Upload a new one to replace it.")

    st.markdown("---")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.resume_text = None # Also clear resume context on chat clear
        st.session_state.resume_uploaded = False
        st.session_state.current_file_name = None
        st.rerun() # Rerun the app to reflect changes immediately


# --- Main Chat Interface ---

# Display prior chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input
if prompt := st.chat_input("What would you like to do? (e.g., 'Review my resume', 'Suggest improvements')"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare context for Gemini
    # Construct the history in the format required by the API (list of Content objects)
    gemini_history = []
    system_instruction = "You are a helpful AI assistant." # Base instruction

    # Dynamically add resume context if available
    if st.session_state.resume_text:
        system_instruction += (
            "\n\nThe user has uploaded the following resume. Use this text "
            "when answering questions about their resume:\n\n"
            f"--- RESUME START ---\n{st.session_state.resume_text}\n--- RESUME END ---"
        )
        # You could also add specific resume analysis instructions here if needed.
        # e.g., "Focus on identifying key skills, areas for improvement, and tailoring suggestions."

    # Add system instruction first if it's complex (optional but can be good practice)
    # Note: For basic gemini-pro, system instructions might be less impactful than prepending context.
    # For newer models (like 1.5 Pro), the system_instruction parameter is more robust.
    # Let's prepend context to the user prompt for broader compatibility.

    full_prompt = prompt
    if st.session_state.resume_text:
        # Prepend context to the *latest* user message for focus
         full_prompt = (
            f"User has provided this resume:\n--- RESUME START ---\n{st.session_state.resume_text}\n--- RESUME END ---\n\n"
            f"Based on this resume, the user asks: {prompt}"
        )


    # Build the chat history for the API call
    # The GenAI Python SDK expects a list where user/model roles alternate.
    # We need to filter/format st.session_state.messages accordingly.
    api_history = []
    for msg in st.session_state.messages[:-1]: # Exclude the latest user prompt as it's handled separately
         # Map role 'assistant' to 'model' for the API
        api_role = 'model' if msg["role"] == 'assistant' else msg["role"]
        api_history.append(types.Content(role=api_role, parts=[types.Part(text=msg["content"])]))


    # Generate response
    try:
        with st.spinner("Thinking..."):
            # Start a chat session to send history correctly
            config = types.GenerateContentConfig(system_instruction=full_prompt)
            
            response = model.models.generate_content(
                
                model="gemini-2.5-pro-exp-03-25",
                contents = api_history,
                config= config

                )
            
            # chat = model.models (history=api_history)
            # response = chat.send_message(full_prompt) # Send the potentially context-prepended prompt

            # client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            # response = client.models.generate_content(prompt)

        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(response.text)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"An error occurred: {e}")
        # Optionally remove the last user message if the API call failed significantly
        # st.session_state.messages.pop()


# Add a placeholder if the chat is empty
if not st.session_state.messages:
     st.info("Upload your resume using the sidebar and start chatting!")