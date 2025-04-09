import os
import re
from docx import Document
import PyPDF2
import io

def extract_text_to_markdown(uploaded_file):
    """
    Extracts text from an uploaded PDF, DOCX, or TXT file and returns it as Markdown-formatted text.
    
    Args:
        uploaded_file (UploadedFile): Streamlit UploadedFile object
        
    Returns:
        str: Extracted text formatted in Markdown
    """
    # Get file extension
    file_name = uploaded_file.name
    _, ext = os.path.splitext(file_name)
    ext = ext.lower()

    # Read file content based on type
    if ext == '.pdf':
        text = _extract_text_from_pdf(uploaded_file)
    elif ext == '.docx':
        text = _extract_text_from_docx(uploaded_file)
    elif ext == '.txt':
        text = _extract_text_from_txt(uploaded_file)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    return _convert_to_markdown(text)

def _extract_text_from_pdf(uploaded_file):
    """Extracts text from PDF using PyPDF2"""
    text = []
    with io.BytesIO(uploaded_file.getvalue()) as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text.append(page.extract_text() or "")
    return "\n".join(text)

def _extract_text_from_docx(uploaded_file):
    """Extracts text from DOCX"""
    with io.BytesIO(uploaded_file.getvalue()) as f:
        doc = Document(f)
        return "\n".join([para.text for para in doc.paragraphs])

def _extract_text_from_txt(uploaded_file):
    """Extracts text from TXT"""
    return uploaded_file.getvalue().decode("utf-8")

def _convert_to_markdown(text):
    """Converts raw text to Markdown with basic formatting"""
    # Convert bullet points
    text = re.sub(r'(?m)^\s*[•●▪]\s*', '- ', text)
    
    # Convert numbered lists
    text = re.sub(r'(?m)^\s*(\d+)\.\s*', r'\1. ', text)
    
    # Bold section headers
    text = re.sub(r'(?m)^([A-Z][A-Z\s\-]+:?)$', r'**\1**', text)
    
    # Preserve paragraph breaks
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    
    return text