FROM python:3.11-slim

WORKDIR /app

# Copy only the script and dependencies
COPY nest_thermostat_control.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Run script when container starts
CMD ["python", "nest_thermostat_control.py", "--config", "config.json"]
