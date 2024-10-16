# Build stage
FROM --platform=linux/amd64 python:3.11 AS builder

# Set the working directory in the build stage
WORKDIR /build

# Copy only the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code to the build stage
COPY . .

# Production stage
FROM --platform=linux/amd64 python:3.11

# Set the working directory in the production stage
WORKDIR /app

# Copy the installed dependencies from the build stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Install gunicorn
RUN pip install gunicorn==20.1.0

# Copy the application code to the production stage
COPY . .

# Expose the port for the Flask application
EXPOSE 5000

# Start the Flask application
CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "--log-file", "log.txt", "--bind", "0.0.0.0:5000", "main:app"]
#CMD ["python", "main.py"]