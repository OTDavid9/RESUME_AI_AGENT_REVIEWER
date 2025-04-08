import os
from google import genai
from google.genai import types
from typing import List, Dict
import textract
from  dotenv import load_dotenv

load_dotenv()
 
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')

def extract_text_from_file(filepath: str) -> str:
    try:
        text = textract.process(filepath)
        return text.decode("utf-8")
    except Exception as e:
        return f"Failed to extract text: {e}"

def review_resume(resume_text: str) -> dict:
    """Analyze resume and provide improvement suggestions."""
    prompt = f"""
You are an expert career advisor. Analyze the following resume text and provide:
- Key strengths
- Missing or weak areas (skills, experience, formatting, etc.)
- Suggestions for improvement
Resume:
{resume_text}
"""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(prompt)
    
    return {
        "analysis": response.text
    }


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

def main():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    memory = ChatMemory(max_messages=20)  # Keep last 20 messages
    
    # Configure tools
    config = types.GenerateContentConfig(
        tools=[ review_resume

        ],
        system_instruction="""You are a multi-functional assistant. You can:
        - Provide financial advice and calculations
        - Recommend laptops from our database
        - Create new employee records
        - Get users' embedding using their BVN
        Be clear about which service you're using."""
    )
    
    print("Financial/Tech Advisor Chat (type 'quit' to exit or 'clear' to reset)")
    print("I can help to review your resume")
    
    
    while True:
        try:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye! Have a great day!")
                break
                
            if user_input.lower() == 'clear':
                memory.clear()
                print("Conversation history cleared.")
                continue
                
            if not user_input.strip():
                continue
            
            # Add user message to memory
            memory.add_message("user", user_input)
            
            print("Advisor: ", end='', flush=True)
            
            # Generate response with full history
            response = client.models.generate_content(
                model="gemini-2.5-pro-exp-03-25",
                contents=memory.get_history(),
                config=config,
            )
            
            if response.text:
                print(response.text)
                # Add assistant response to memory
                memory.add_message("model", response.text)
            else:
                print("[DEBUG] No text response generated")
                print("I couldn't generate a response. Please try again.")
                
        except KeyboardInterrupt:
            print("\nGoodbye! Have a great day!")
            break
        except Exception as e:
            print(f"\n[DEBUG] Error occurred: {type(e).__name__}: {e}")
            print("Please try again or type 'quit' to exit.")

if __name__ == "__main__":    
    main()