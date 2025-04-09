import streamlit as st
import os
from google import genai
from google.genai import types
from typing import List, Dict
import io
from dotenv import load_dotenv
from resume import (
    _extract_text_from_pdf,
    _extract_text_from_docx,
    _extract_text_from_txt,
    _convert_to_markdown
)

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

# --- Core Functions ---
@st.cache_data(show_spinner="Extracting text from resume...")
def extract_text_to_markdown(uploaded_file):
    """Extracts text from uploaded file and returns as Markdown"""
    file_name = uploaded_file.name
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()

    if ext == '.pdf':
        text = _extract_text_from_pdf(uploaded_file)
    elif ext == '.docx':
        text = _extract_text_from_docx(uploaded_file)
    elif ext == '.txt':
        text = _extract_text_from_txt(uploaded_file)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    return _convert_to_markdown(text)

@st.cache_resource
def load_model():
    """Loads the Gemini model"""
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class ChatMemory:
    """Class to manage conversation history"""
    def __init__(self, max_messages: int = 10):
        self.history: List[types.Content] = []
        self.max_messages = max_messages
    
    def add_message(self, role: str, content: str):
        """Add a message to the history"""
        self.history.append(
            types.Content(
                role=role,
                parts=[types.Part(text=content)] 
            )
        )
        # Trim history if it exceeds max messages
        if len(self.history) > self.max_messages:
            self.history = self.history[-self.max_messages:]
    
    def get_history(self) -> List[types.Content]:
        """Get the conversation history"""
        return self.history
    
    def clear(self):
        """Clear conversation history"""
        self.history = []

 # --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "resume_text" not in st.session_state:
    st.session_state.resume_text = None

if "resume_uploaded" not in st.session_state:
    st.session_state.resume_uploaded = False

# --- Sidebar ---
with st.sidebar:
    st.header("Upload Resume")
    uploaded_file = st.file_uploader(
        "Choose a file (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=False
    )

    if uploaded_file is not None:
        if not st.session_state.resume_uploaded or st.session_state.get("current_file_name") != uploaded_file.name:
            try:
                extracted_text = extract_text_to_markdown(uploaded_file)
                if extracted_text:
                    st.session_state.resume_text = extracted_text
                    st.session_state.resume_uploaded = True
                    st.session_state.current_file_name = uploaded_file.name
                    st.success("✅ Resume processed successfully!")
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
                st.session_state.resume_text = None
                st.session_state.resume_uploaded = False
                st.session_state.current_file_name = None

    elif st.session_state.resume_uploaded:
        st.info("Resume was previously uploaded. Upload a new one to replace it.")

    st.markdown("---")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.resume_text = None
        st.session_state.resume_uploaded = False
        st.session_state.current_file_name = None
        st.rerun()

# --- Main Chat Interface ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What would you like to do?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare context
    context = ""
    if st.session_state.resume_text:
        context = f"Here is the user's resume:\n\n{st.session_state.resume_text}\n\n"

    try:
        with st.spinner("Thinking..."):
            # Start chat with context
            # chat = model.start_chat(history=[])
            
            # Send both context and prompt
            # full_prompt = f"{context}User question: {prompt}"
            # response = chat.send_message(full_prompt)
            client = load_model()

            memory = ChatMemory(max_messages=20)  # Keep last 20 messages

            memory.add_message("user", content=st.session_state.resume_text)  
            config = types.GenerateContentConfig(
        tools=[ 

        ],
        system_instruction = """**Resume AI Assistant - System Instructions**

                You are an expert resume analyzer and career advisor with the following capabilities:

                1. **Resume Analysis**:
                - Provide detailed feedback on resume structure, content, and formatting
                - Identify strengths and areas for improvement
                - Check for consistency in formatting and styling

                2. **Content Enhancement**:
                - Suggest powerful action verbs and achievement-oriented language
                - Help quantify accomplishments with metrics where possible
                - Recommend relevant keywords for Applicant Tracking Systems (ATS)

                3. **Tailoring Assistance**:
                - Help customize the resume for specific job descriptions
                - Suggest relevant skills and experiences to highlight
                - Provide industry-specific advice when given the target role

                4. **Career Guidance**:
                - Offer advice on career progression based on the resume
                - Suggest complementary skills to develop
                - Provide interview preparation tips for the roles mentioned

                **Interaction Rules**:
                - Always be professional yet approachable
                - Ask clarifying questions when needed
                - Provide concise, actionable advice
                - Structure responses with clear headings when appropriate
                - Never share personal opinions - base advice on professional best practices
                - When suggesting changes, provide specific examples from the resume

                **Response Format**:
                1. Begin by acknowledging the user's request
                2. Provide analysis in clear sections
                3. Use bullet points for actionable items
                4. Offer to elaborate on any point if needed

                **Special Cases**:
                - If no resume is uploaded, politely remind the user
                - If the request is unclear, ask for clarification
                - If technical terms are used, explain them briefly
                - Always uses answer briefly expect the users demand that your review their resumes"""
    )

            memory.add_message("user", prompt)

            response = client.models.generate_content(
                model="gemini-2.5-pro-exp-03-25",
                contents=memory.get_history(),
                config=config,
            )
            
            # Display response
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"An error occurred: {e}")

if not st.session_state.messages:
    st.info("Upload your resume using the sidebar and start chatting!")
