import json
import base64


def convert_task_to_tes(task_incl_run: dict, default_resources: dict) -> dict:
    task = task_incl_run["task"]
    run_id = task_incl_run["id"]
    task_id = task["id"]

    input_data = task_incl_run.get("input", "")
    if isinstance(input_data, dict):
        input_data = json.dumps(input_data)
    if isinstance(input_data, bytes):
        input_data = base64.b64encode(input_data).decode("utf-8")

    tes_task = {
        "name": f"v6-task-{task_id}-run-{run_id}-{task.get('name', 'unnamed')}",
        "description": f"vantage6 task {task_id}, run {run_id}",
        "executors": [
            {
                "image": task["image"],
                "command": [],
                "env": {
                    "INPUT_FILE": "/app/input.txt",
                },
            }
        ],
        "inputs": [
            {
                "name": "input",
                "path": "/app/input.txt",
                "content": input_data,
                "type": "FILE",
            }
        ],
        "outputs": [
            {
                "name": "output",
                "path": "/app/output.txt",
                "url": f"vantage6://run/{run_id}/result",
                "type": "FILE",
            }
        ],
        "tags": {
            "vantage6_task_id": str(task_id),
            "vantage6_run_id": str(run_id),
            "vantage6_job_id": str(task.get("job_id", "")),
            "vantage6_image": task.get("image", ""),
            "vantage6_init_org_id": str(task.get("init_org", {}).get("id", "")),
            "vantage6_init_user_id": str(task.get("init_user", {}).get("id", "")),
        },
        "volumes": ["/app/"],
    }

    if task.get("databases"):
        db_labels = [db.get("label", "") for db in task["databases"]]
        tes_task["tags"]["vantage6_databases"] = ",".join(db_labels)

    if default_resources:
        resources = {}
        if "cpu_cores" in default_resources:
            resources["cpu_cores"] = default_resources["cpu_cores"]
        if "ram_gb" in default_resources:
            resources["ram_gb"] = default_resources["ram_gb"]
        if "disk_gb" in default_resources:
            resources["disk_gb"] = default_resources["disk_gb"]
        if "preemptible" in default_resources:
            resources["preemptible"] = default_resources["preemptible"]
        if "zones" in default_resources:
            resources["zones"] = default_resources["zones"]
        if "backend_parameters" in default_resources:
            resources["backend_parameters"] = default_resources["backend_parameters"]
        if "backend_parameters_strict" in default_resources:
            resources["backend_parameters_strict"] = default_resources[
                "backend_parameters_strict"
            ]
        if resources:
            tes_task["resources"] = resources

    return tes_task
