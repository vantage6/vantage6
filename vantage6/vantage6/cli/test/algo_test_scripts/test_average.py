from vantage6.cli.test.algo_test_scripts.algo_test_template import (
    AlgoTestTemplate,
    Result,
)


class AverageTest(AlgoTestTemplate):
    def __init__(self, client):
        super().__init__(client)

    def test(
        self,
        algorithm_image: str | None = None,
        input_: dict | None = None,
        database: str | None = None,
    ) -> Result:
        """
        Test the average algorithm.

        Parameters:
        -----------
        input_ : dict
            The input for the algorithm.
        database : str
            The label of the database to use. Defaults to "default".

        Returns:
        --------
        dict[str, bool]
            A dictionary indicating the success of the test and the result.
        """
        algorithm_image = algorithm_image or "harbor2.vantage6.ai/demo/average"
        database = database or "default"
        input_ = input_ or {
            "method": "central_average",
            "args": [],
            "kwargs": {"column_name": "Age"},
        }

        task = self.client.task.create(
            collaboration=1,
            organizations=[1],
            name="test_average_task",
            image=algorithm_image,
            description="",
            input_=input_,
            databases=[{"label": database}],
        )

        task_id = task["id"]

        task_result = self.client.wait_for_results(task_id)

        passed = True
        try:
            assert (
                task_result.get("data")[0].get("result")
                == '{"average": 27.613448844884488}'
            )
        except AssertionError:
            passed = False

        return Result(passed=passed, result=task_result)


# this is needed for the test runner
def get_test_class(client):
    return AverageTest(client)
