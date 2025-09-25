FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install the package in development mode
RUN pip install -e .

# Expose ports for API and UI
EXPOSE 8000
EXPOSE 8501

# Set environment variables
ENV PYTHONPATH=/app
ENV API_URL=http://localhost:8080

# Run the web interface
CMD ["python", "-m", "quality_engineering_agentic_framework.web.run_web"]