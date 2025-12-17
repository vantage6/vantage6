API response structure
----------------------

Each API endpoint returns a JSON response. All responses are structured in the
same way, loosely following HATEOAS rules. An example is detailed below:

.. code:: python

  >>> client.task.get(task_id)
  {
      "id": 1,
      "name": "test",
      "results": "/api/result?task_id=1",
      "image": "harbor2.vantage6.ai/testing/v6-test-py",
      ...
  }

The response for this task includes a link to the results that are attached to
this task. More detail on the results are provided when collecting the response
for that link.
