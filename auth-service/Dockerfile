# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential gcc

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Debug step to list installed packages
RUN pip list

# Make port 5010 available to the world outside this container
EXPOSE 5010

# Run Gunicorn when the container launches with debug logging and timeout
CMD ["gunicorn", "-b", "0.0.0.0:5010", "app:create_app()", "--workers=3", "--timeout=120", "--log-level=debug", "--capture-output"]
