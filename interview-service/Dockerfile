# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg and ffprobe
RUN apt-get update && apt-get install -y ffmpeg

# Set environment variables
ENV FFMPEG_LOCATION=/usr/bin/ffmpeg

# Make port 5013 available to the world outside this container
EXPOSE 5013

# Define environment variable
ENV NAME InterviewBot

# Run app.py when the container launches
CMD ["python", "app.py"]
