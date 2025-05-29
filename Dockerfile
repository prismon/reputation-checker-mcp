# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY url_reputation_checker/ ./url_reputation_checker/
COPY pyproject.toml .

# Install the package
RUN pip install -e .

# Expose the MCP server port (default 5000)
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_SERVER_HOST=0.0.0.0
ENV MCP_SERVER_PORT=5000

# Run the MCP server with proper signal handling
CMD ["python", "-m", "url_reputation_checker"]