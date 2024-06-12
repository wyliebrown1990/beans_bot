# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential gcc

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5011 available to the world outside this container
EXPOSE 5011

# Run Gunicorn when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:5011", "app:app"]
