API response structure
----------------------

Each API endpoint returns a JSON response. All responses are structured in the
same way, according to the HATEOAS constraints. An example is detailed below:
::

  >>> client.task.get(task_id)
  {
      "id": 1,
      "name": "test",
      "results": [
          {
              "id": 2,
              "link": "/api/result/2",
              "methods": [
                  "PATCH",
                  "GET"
              ]
          }
      ],
      "image": "harbor2.vantage6.ai/testing/v6-test-py",
      ...
  }

The response for this task includes the results that are attached to this task.
In compliance with HATEOAS, a link is supplied to the link where the result can
be viewed in more detail.
