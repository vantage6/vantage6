#!/usr/bin/env python3
# Quickly send 'average' task to local development server

from vantage6.client import Client

# Config for local dev server
config = {
    'server_url': "http://localhost",
    'server_port': 5000,
    'server_api': "/api",
    # Your user name goes here
    # 'username': "phobos",
    'username': "titan",
    # This is just a test password for quick local development server
    # 'password': "test-password-two-orbit",
    'password': "test-password-cloudy-orbit",
    'organization_key': None,
}

# Initialize the client object, and run the authentication
client = Client(config['server_url'], config['server_port'], config['server_api'])
client.authenticate(config['username'], config['password'])
client.setup_encryption(config['organization_key'])

# Define some input for the averaging algorithm
input_ = {
    #'method': 'partial_average',
    'method': 'central_average',
    'kwargs': {
        'column_name': 'value'
    },
}

# Create a task.
average_task_partials = client.task.create(
    collaboration=1,
    organizations=[1],
    name="letters-partial-average-task",
    image="harbor2.vantage6.ai/demo/average",
    description='',
    databases=[
        {'label': 'letters'}
    ],
    input_=input_
)

# Wait for results to be ready
print("Waiting for results")
client.wait_for_results(average_task_partials['id'])

# Get the results
result_info = client.result.from_task(task_id=average_task_partials['id'])

# Try to print them nicely (depends on the algo..)
print()
print("Results:")
for data in result_info['data']:
    print(data['result'])
    print()
