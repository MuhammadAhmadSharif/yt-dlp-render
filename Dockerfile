# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy the repository contents
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install ffmpeg (optional, recommended for yt-dlp)
RUN apt-get update && apt-get install -y ffmpeg

# Expose port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]