# # Use an official Python runtime as a base image
FROM python:3.10-slim

WORKDIR /app

# First downgrade pip to version that works with textract
RUN pip install --no-cache-dir pip==23.3.2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
