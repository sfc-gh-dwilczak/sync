FROM python:3.9-slim

# Install ffmpeg which is required by moviepy
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV AWS_ACCESS_KEY_ID=A....
ENV AWS_SECRET_ACCESS_KEY=...
ENV AWS_DEFAULT_REGION=us-east-1

# Copy and install Python dependencies
COPY requirements.txt .
COPY s3/ s3/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app will run on
EXPOSE 80

VOLUME ["/s3"]

# Start the FastAPI app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]