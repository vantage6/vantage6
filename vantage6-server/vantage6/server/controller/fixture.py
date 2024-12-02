import uuid
import logging

import vantage6.server.model as db
from vantage6.server.model.base import Database
from vantage6.server import RESOURCES, RESOURCES_PATH, DefaultRole
from vantage6.server.permission import PermissionManager
from vantage6.common.enum import RunStatus
from vantage6.common.serialization import serialize
from vantage6.common import bytes_to_base64s

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


# TODO maybe move this function to a more general location (utils?)
def _is_valid_uuid(uuid_to_test):
    """
    Check if uuid_to_test is a valid UUID.

     Parameters
    ----------
    uuid_to_test : str

     Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.
    """
    try:
        uuid_obj = uuid.UUID(uuid_to_test)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def load(fixtures: dict, drop_all: bool = False) -> None:
    """
    Load fixtures (i.e. fixed resources to test functionality) into the
    database.

    Parameters
    ----------
    fixtures : dict
        Dictionary containing the fixtures to load into the database.
    drop_all : bool
        If `True` all tables in the database will be dropped before loading
    """
    # TODO we are not sure the DB is connected here....

    if drop_all:
        Database().drop_all()

    # If the server has never been started yet, no rules have been created yet.
    # In that case, create them here so that the created users have
    # permissions.
    if not db.Rule.get():
        permissions = PermissionManager(RESOURCES_PATH, RESOURCES, DefaultRole)
        permissions.load_rules_from_resources(RESOURCES_PATH, RESOURCES)

    log.info("Create Organizations and Users")
    for org in fixtures.get("organizations", {}):
        # print(org)

        # create organization
        organization = db.Organization(
            **{
                k: org[k]
                for k in [
                    "name",
                    "domain",
                    "address1",
                    "address2",
                    "zipcode",
                    "country",
                    "public_key",
                ]
            }
        )
        organization.save()
        log.debug(f"processed organization={organization.name}")
        superuserrole = db.Role(
            name="super",
            description="Super user",
            rules=db.Rule.get(),
            organization=organization,
        )
        superuserrole.save()
        # create users
        for usr in org.get("users", {}):
            user = db.User(**usr)
            user.roles = [superuserrole]
            user.organization = organization
            user.save()
            log.debug(f"processed user={user.username}")

    log.info("Create collaborations")
    for col in fixtures.get("collaborations", {}):
        # create collaboration
        collaboration = db.Collaboration(
            name=col.get("name"), encrypted=col.get("encrypted", True)
        )
        log.debug(f"processed collaboration={collaboration.name}")

        # append organizations to the collaboration

        for participant in col.get("participants", {}):
            if (
                not isinstance(participant, dict)
                or not participant.get("name")
                or not participant.get("api_key")
            ):
                log.error(
                    "Collaboration participants should contain the "
                    "fields 'name' and 'api_key'. This is not the case "
                    f"for participant {participant} in collaboration "
                    f"{collaboration.name}"
                )
                exit(1)

            org_name = participant.get("name")
            node_api_key = participant.get("api_key")

            # check if api key is valid uuid
            if not _is_valid_uuid(node_api_key):
                log.error(f"API key '{node_api_key}' is not a valid UUID!")
                exit(1)

            organization = db.Organization.get_by_name(org_name)
            collaboration.organizations.append(organization)
            log.debug(f"added {org_name} to the collaboration")

            node = db.Node(
                organization=organization,
                collaboration=collaboration,
                name=f"{organization.name} - {collaboration.name} Node",
                api_key=node_api_key,
            )
            node.save()
            log.debug(f"added node {node.name} to {collaboration.name}")

        collaboration.save()

        # append dummy tasks to the collaboration
        log.debug("Processing Task Assignments")
        for image in col.get("tasks", {}):
            init_org = collaboration.organizations[0]
            task = db.Task(
                name="Example task",
                image=image,
                collaboration=collaboration,
                job_id=db.Task.next_job_id(),
                init_org=init_org,
                init_user=db.User.get()[0],
            )

            for organization in collaboration.organizations:
                run = db.Run(
                    task=task,
                    input=bytes_to_base64s(serialize({"a": "b"})),
                    organization=organization,
                    status=RunStatus.PENDING,
                )
                run.save()

            task.save()
            log.debug(f"Processed task {task.name}")
