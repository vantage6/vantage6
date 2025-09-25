"""
Cleanup jobs in the task namespace.
"""

import argparse

from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client import ApiException
from kubernetes.config.config_exception import ConfigException

from vantage6.common.globals import APPNAME

from vantage6.node.k8s.task_cleanup import delete_job_related_pods


def _is_vantage6_task_job(job: k8s_client.V1Job) -> bool:
    # Vantage6 task jobs can be identified by their name, which is of the form
    # "vantage6-run-<run_id>"
    return job.metadata.name.startswith(f"{APPNAME}-run-")


def _get_jobs(
    namespace: str, batch_api: k8s_client.BatchV1Api
) -> list[k8s_client.V1Job]:
    try:
        return batch_api.list_namespaced_job(namespace=namespace).items
    except ApiException as exc:
        print(f"Failed to list jobs in namespace {namespace}: {exc}")
        return []


def _get_job_run_id(job: k8s_client.V1Job) -> int | None:
    annotations = job.metadata.annotations or {}
    try:
        return int(annotations.get("run_id"))
    except ValueError:
        print(f"Job '{job.metadata.name}' has no run_id annotation, skipping")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup Vantage6 task jobs")
    parser.add_argument("--namespace", type=str, default=None, help="Task namespace")
    args = parser.parse_args()

    namespace = args.namespace
    print(f"Cleaning up Vantage6 task jobs in namespace '{args.namespace}'")

    # Load Kubernetes configuration (in-cluster first, fallback to kubeconfig)
    try:
        k8s_config.load_incluster_config()
    except ConfigException:
        try:
            k8s_config.load_kube_config()
        except ConfigException as exc:
            print(f"Failed to load Kubernetes configuration: {exc}")
            return 1

    core_api = k8s_client.CoreV1Api()
    batch_api = k8s_client.BatchV1Api()

    jobs = _get_jobs(namespace, batch_api)

    deletions = 0
    for job in jobs:
        if not _is_vantage6_task_job(job):
            continue

        run_id = _get_job_run_id(job)
        if run_id is None:
            continue

        # Use shared cleanup to delete job, pods and related secret
        job_name = job.metadata.name
        print(f"Deleting job '{job_name}' (run_id={run_id})")
        delete_job_related_pods(
            run_id=run_id,
            container_name=f"{APPNAME}-run-{run_id}",
            namespace=namespace,
            core_api=core_api,
            batch_api=batch_api,
        )
        deletions += 1

    if deletions == 0:
        print(f"No Vantage6 task jobs found to delete in namespace '{namespace}'")
    else:
        print(f"Deleted {deletions} Vantage6 task job(s) in namespace '{namespace}'")


if __name__ == "__main__":
    main()
