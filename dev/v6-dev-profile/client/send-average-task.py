from vantage6.client import Client
# This is a short script to send a task to the three nodes.
# In a federated way.
# Meaning, we'll send a task to node Mars, and Mars will send tasks to Jupiter, Saturn and Mars (itself) computing the local average of their dataset

def wait_and_print_results(task_id):
    # Wait for results to be ready
    print("Waiting for results")
    client.wait_for_results(task_id)

    results = client.result.from_task(task_id=task_id)

    # Try to print them nicely (depends on the algo..)
    print()
    print("Results:")
    for data in results['data']:
        print(data['result'])
        print()

config = {
    'server_url': "http://127.0.6.1",
    'server_port': 80,
    'server_api': "/api",
    'username': "phobos",
    # just a test password, can be found in entities.yaml
    'password': "test-password-two-orbit",
    'organization_key': None,
}

client = Client(config['server_url'], config['server_port'], config['server_api'])
client.authenticate(config['username'], config['password'])
client.setup_encryption(config['organization_key'])

# Define some input for the average algorithm
input_ = {
    'method': 'partial_average',
    'kwargs': {
        'column_name': 'value'
    }
}

# average_task_partials = client.task.create(
#     collaboration=1,
#     organizations=[1],
#     name="letters-average-task-five",
#     image="harbor2.vantage6.ai/demo/average",
#     description='Demo task',
#     databases=[
#         {'label': 'letters'}
#     ],
#     input_=input_
# )

# wait_and_print_results(average_task_partials['id'])


# Create another task that uses central function
input_ = {
    'method': 'central_average',
    'kwargs': {
        'column_name': 'value'
    }
}

average_task_central = client.task.create(
    collaboration=1,
    # in organization 1 (Mars) the aggregation will happen
    # this is, all the partial results from all algorithms will
    # be aggregated
    organizations=[1],
    name="letters-average-task",
    image="harbor2.vantage6.ai/demo/average",
    description='Demo task, central',
    # we are using the 'letters' datasaet
    databases=[
        {'label': 'letters'}
    ],
    input_=input_
)

wait_and_print_results(average_task_central['id'])
