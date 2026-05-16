FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg nodejs npm && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements separately for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port for UptimeRobot pings
EXPOSE 8080

# Environment variable for the port (Render will override this)
ENV PORT=8080

CMD ["python", "main.py"]
