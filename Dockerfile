FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Use Gunicorn instead of Python directly
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app