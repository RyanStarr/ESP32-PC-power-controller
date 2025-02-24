#Basic Python Alpine image
FROM python:3.12-alpine

# Set the running directory
WORKDIR /app

# Python requirements file
COPY requirements.txt .

# Install requirement dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy python folder
COPY python/ .

# Set the default command to run a Python script (change "app.py" as needed)
CMD ["python", "power-monitor.py"]
