# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Create a non-root user with an explicit UID and add permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY --chown=appuser . .

# Create directory for uploads if it doesn't exist and ensure permissions
RUN mkdir -p uploads && chown -R appuser uploads

# Switch to the non-root user
USER appuser

# Make port 7860 available to the world outside this container
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]
