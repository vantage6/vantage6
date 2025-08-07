from vantage6.client import UserClient as Client

import config

client = Client(config.server_url, config.server_port, config.server_api, log_level='debug')

client.authenticate(config.username, config.password)
client.setup_encryption(config.organization_key)
client.organization.list(collaboration=1, fields=['id', 'name'])

input_ = {
    'method': 'central',
    'kwargs': {'arg1': 'age'}
}

average_task = client.task.create(
   collaboration=1,
   organizations=[1],
   name="dhd-test-task-1",
   image="localhost:5000/dhd-test-algorithm:latest",
   description='',
   input_=input_,
   databases=[
      {'label': 'default'}
   ]
)
print("Waiting for results")
task_id = average_task['id']

result = client.retrieve_results(task_id)
print(f"------------------------------------")
print(f"wait for results: {result}")
task_info = client.task.get(task_id, include_results=False)
print(f"------------------------------------")
print(f"task info: {task_info}")

result_info = client.result.from_task(task_id=task_id)
print(f"------------------------------------")
print(f"result info: {result_info}")

## clear results
client.task.cleanup(task_id=task_id, include_input=True)
print(f"------------------------------------")