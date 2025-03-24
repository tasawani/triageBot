# Use an official Python runtime as a base image
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . .
# Copy the service account key file
COPY hospitalbot-service-key.json /app/service-account.json

# Set the environment variable inside the container
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/service-account.json"

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Command to run the application
CMD ["python", "main.py"]
