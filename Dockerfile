FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    netcat-openbsd \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip uninstall -y bson pymongo && pip install pymongo
# Copy entrypoint first and give it permissions
COPY ./entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Copy project
COPY . .

# Make sure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"] 