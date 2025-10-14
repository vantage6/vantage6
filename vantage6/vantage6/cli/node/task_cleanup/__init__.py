import logging

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from vantage6.common import logger_name

log = logging.getLogger(logger_name(__name__))


def delete_job_related_pods(
    run_id: int,
    container_name: str,
    namespace: str,
    core_api: k8s_client.CoreV1Api,
    batch_api: k8s_client.BatchV1Api,
) -> None:
    """
    Deletes all the PODs created by a Kubernetes job in a given namespace

    Parameters
    ----------
    run_id: int
        Server run identifier
    container_name: str
        Name of the container
    namespace: str
        Namespace where the container is located
    core_api: k8s_client.CoreV1Api
        Kubernetes Core API instance
    batch_api: k8s_client.BatchV1Api
        Kubernetes Batch API instance
    """
    log.info(
        "Cleaning up kubernetes Job %s (run_id = %s) and related PODs",
        container_name,
        run_id,
    )

    __delete_job(container_name, namespace, batch_api)

    job_selector = f"job-name={container_name}"
    job_pods_list = core_api.list_namespaced_pod(namespace, label_selector=job_selector)
    for job_pod in job_pods_list.items:
        __delete_pod(job_pod.metadata.name, namespace, core_api)

    __delete_secret(container_name, namespace, core_api)


def __delete_secret(
    secret_name: str, namespace: str, core_api: k8s_client.CoreV1Api
) -> None:
    """
    Deletes a secret in a given namespace

    Parameters
    ----------
    secret_name: str
        Name of the secret
    namespace: str
        Namespace where the secret is located
    core_api: k8s_client.CoreV1Api
        Kubernetes Core API instance
    """
    try:
        core_api.delete_namespaced_secret(name=secret_name, namespace=namespace)
        log.info(
            "Removed kubernetes Secret %s in namespace %s",
            secret_name,
            namespace,
        )
    except ApiException as exc:
        if exc.status == 404:
            log.debug("No secret %s to remove in namespace %s", secret_name, namespace)
        else:
            log.error("Exception when deleting namespaced secret: %s", exc)


def __delete_job(
    job_name: str, namespace: str, batch_api: k8s_client.BatchV1Api
) -> None:
    """
    Deletes a job in a given namespace

    Parameters
    ----------
    job_name: str
        Name of the job
    namespace: str
        Namespace where the job is located
    batch_api: k8s_client.BatchV1Api
        Kubernetes Batch API instance
    """
    log.info(
        "Cleaning up kubernetes Job %s and related PODs",
        job_name,
    )
    try:
        # Check if the job exists before attempting to delete it
        job = batch_api.read_namespaced_job(name=job_name, namespace=namespace)
        if job:
            batch_api.delete_namespaced_job(name=job_name, namespace=namespace)
        else:
            log.warning(
                "Job %s not found in namespace %s, skipping deletion",
                job_name,
                namespace,
            )
    except ApiException as exc:
        if exc.status == 404:
            log.warning(
                "Job %s not found in namespace %s, skipping deletion",
                job_name,
                namespace,
            )
        else:
            log.error("Exception when deleting namespaced job: %s", exc)


def __delete_pod(pod_name: str, namespace: str, core_api: k8s_client.CoreV1Api) -> None:
    """
    Deletes a job in a given namespace

    Parameters
    ----------
    pod_name: str
        Name of the job
    namespace: str
        Namespace where the job is located
    core_api: k8s_client.CoreV1Api
        Kubernetes Core API instance
    """
    log.info("Cleaning up kubernetes pod %s in namespace %s", pod_name, namespace)
    try:
        # Check if the job exists before attempting to delete it
        job = core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
        if job:
            core_api.delete_namespaced_pod(name=pod_name, namespace=namespace)
        else:
            log.warning(
                "Pod %s not found in namespace %s, skipping deletion",
                pod_name,
                namespace,
            )
    except ApiException as exc:
        if exc.status == 404:
            log.warning(
                "Pod %s not found in namespace %s, skipping deletion",
                pod_name,
                namespace,
            )
        else:
            log.error("Exception when deleting namespaced job: %s", exc)
