"""
Shared logic for persisting a validated algorithm payload to the database.

Used by the HTTP POST /algorithm handler and by config-driven init seeding.
Reviewer notification email is handled in the REST resource only.
"""

import logging

from vantage6.common import logger_name
from vantage6.common.docker.addons import (
    get_digest,
    get_image_name_wo_tag,
    parse_image_name,
)
from vantage6.common.globals import DATAFRAME_MULTIPLE_KEYWORD

from vantage6.algorithm.store.model.algorithm import Algorithm as db_Algorithm
from vantage6.algorithm.store.model.allowed_argument_value import AllowedArgumentValue
from vantage6.algorithm.store.model.argument import Argument
from vantage6.algorithm.store.model.database import Database
from vantage6.algorithm.store.model.function import Function
from vantage6.algorithm.store.model.ui_visualization import UIVisualization

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def resolve_image_digest(image_name: str, config: dict) -> tuple[str, str | None]:
    """
    Resolve Docker image name and digest (mirrors AlgorithmBaseResource._get_image_digest).

    Parameters
    ----------
    image_name : str
        Full image reference including tag or digest.
    config : dict
        Algorithm store configuration (for private_docker_registries).

    Returns
    -------
    tuple[str, str | None]
        ``(image_with_tag_or_digest, digest)`` where digest may be None if lookup
        failed.
    """
    try:
        registry, _, tag = parse_image_name(image_name)
        image_wo_tag = get_image_name_wo_tag(image_name)
    except Exception as e:
        raise ValueError(f"Invalid image name: {image_name}") from e

    if not tag.startswith("sha256:"):
        image_and_tag = f"{image_wo_tag}:{tag}"
    else:
        image_and_tag = image_wo_tag

    digest = get_digest(image_name)
    if digest:
        log.info("Digest obtained succesfully!")
        return image_and_tag, digest

    log.debug("Failed to get digest without authentication...")

    docker_registries = config.get("private_docker_registries", [])
    registry_user = None
    registry_password = None
    for reg in docker_registries:
        if reg["registry"] == registry:
            registry_user = reg.get("username")
            registry_password = reg.get("password")
            break
    if registry_user and registry_password:
        log.info("Retrying to get digest with authentication...")
        digest = get_digest(
            full_image=image_name,
            registry_username=registry_user,
            registry_password=registry_password,
        )
        if digest:
            log.info("Digest obtained succesfully!")
        else:
            log.error("Failed to get digest with authentication!")
    else:
        log.error("Failed to get digest!")

    return image_and_tag, digest


def create_algorithm_from_validated_data(
    data: dict,
    developer_id: int,
    config: dict,
    resolved_image: str,
    digest: str,
    auto_approve: bool = False,
) -> db_Algorithm:
    """
    Persist an algorithm and nested functions after schema validation.

    Parameters
    ----------
    data : dict
        Output of :class:`~AlgorithmInputSchema`.load().
    developer_id : int
        Database user id of the developer (root user during init seeding).
    config : dict
        Store configuration.
    resolved_image : str
        Image string after digest resolution (tag normalized).
    digest : str
        Image digest string.
    auto_approve : bool
        If True, approve the algorithm immediately after save (used for
        ``link_algorithms`` / config-driven seeding). Otherwise, approval follows
        ``dev.disable_review`` like a normal API submission.

    Returns
    -------
    db_Algorithm
        The saved algorithm model.
    """
    algorithm = db_Algorithm(
        name=data["name"],
        description=data.get("description", ""),
        image=resolved_image,
        partitioning=data["partitioning"],
        vantage6_version=data["vantage6_version"],
        code_url=data["code_url"],
        documentation_url=data.get("documentation_url", None),
        digest=digest,
        developer_id=developer_id,
        submission_comments=data.get("submission_comments", None),
    )
    algorithm.save()

    if auto_approve or config.get("dev", {}).get("disable_review", False):
        algorithm.approve()

    for function in data["functions"]:
        func = Function(
            name=function["name"],
            display_name=function.get("display_name", ""),
            description=function.get("description", ""),
            step_type=function["step_type"],
            standalone=function.get("standalone", True),
            algorithm_id=algorithm.id,
        )
        func.save()
        for argument in function.get("arguments", []):
            arg = Argument(
                name=argument["name"],
                display_name=argument.get("display_name", ""),
                description=argument.get("description", ""),
                type_=argument["type_"],
                has_default_value=argument.get("has_default_value", False),
                default_value=argument.get("default_value", None),
                conditional_operator=argument.get("conditional_operator", None),
                conditional_value=argument.get("conditional_value", None),
                is_frontend_only=argument.get("is_frontend_only", False),
                function_id=func.id,
            )
            arg.save()
        for argument in function.get("arguments", []):
            arg = Argument.get_by_name(argument["name"], func.id)
            if argument.get("conditional_on"):
                conditional_on = Argument.get_by_name(
                    argument["conditional_on"], func.id
                )
                arg.conditional_on_id = conditional_on.id
                arg.save()
            if argument.get("allowed_values", []):
                for value in argument["allowed_values"]:
                    allowed_value = AllowedArgumentValue(
                        value=str(value), argument_id=arg.id
                    )
                    allowed_value.save()
        for database in function.get("databases", []):
            db_ = Database(
                name=database["name"],
                description=database.get("description", ""),
                function_id=func.id,
                multiple=database.get(DATAFRAME_MULTIPLE_KEYWORD, False),
            )
            db_.save()
        for visualization in function.get("ui_visualizations", []):
            vis = UIVisualization(
                name=visualization["name"],
                description=visualization.get("description", ""),
                type_=visualization["type_"],
                schema=visualization.get("schema", {}),
                function_id=func.id,
            )
            vis.save()

    return algorithm
