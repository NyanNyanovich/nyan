# Use an official Python runtime as a parent image
FROM debian:bookworm-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install 
RUN apt-get update && \
    apt-get install -y python3-pip wget && \
    rm -rf /var/lib/apt/lists/*

# Clone the repository
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt && \
# Download models
    bash download_models.sh
