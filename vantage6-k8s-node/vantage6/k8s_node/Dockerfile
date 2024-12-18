# Use the official Python base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the Python script into the container
COPY *.py requirements.txt /app/

# Copy the 'vantage6' folder (the original v6 classes used by the PoC)  into the container
COPY vantage6 /app/vantage6

RUN pip install -r requirements.txt

# Set the entrypoint to the Python script
ENTRYPOINT ["python", "v6-k8s-node.py"]

