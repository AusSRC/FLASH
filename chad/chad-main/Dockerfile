# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV FLASK_APP=chad
ENV FLASK_RUN_HOST=0.0.0.0

# Install dependencies
RUN apt-get update && apt-get install -y \
    iproute2 \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY frontend/ /app

# Install any needed packages specified in requirements.txt
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "chad:app", "--workers", "4", "--threads", "2"]