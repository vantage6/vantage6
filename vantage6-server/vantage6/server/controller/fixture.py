import uuid
import logging

import vantage6.server.model as db

module_name = __name__.split('.')[-1]
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


def load(fixtures, drop_all=False):
    # TODO we are not sure the DB is connected here....

    # if drop_all:
    #     Database().drop_all()

    log.info("Create Organizations and Users")
    for org in fixtures.get("organizations", {}):
        # print(org)

        # create organization
        organization = db.Organization(**{k: org[k] for k in [
            "name", "domain", "address1", "address2", "zipcode",
            "country", "public_key"
        ]})
        organization.save()
        log.debug(f"processed organization={organization.name}")
        superuserrole = db.Role(name="super", description="Super user",
                                rules=db.Rule.get(), organization=organization)
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
        collaboration = db.Collaboration(name=col.get("name"), encrypted=col.get("encrypted", True))
        log.debug(f"processed collaboration={collaboration.name}")

        # append organizations to the collaboration

        for participant in col.get("participants", {}):
            if not isinstance(participant, dict) \
                    or not participant.get('name') \
                    or not participant.get('api_key'):
                log.error("Collaboration participants should contain the "
                          "fields 'name' and 'api_key'. This is not the case "
                          f"for participant {participant} in collaboration "
                          f"{collaboration.name}")
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
                api_key=node_api_key
            )
            node.save()
            log.debug(f"added node {node.name} to {collaboration.name}")

        collaboration.save()

        # append dummy tasks to the collaboration
        log.debug("Processing Task Assignments")
        for image in col.get("tasks", {}):
            initiator = collaboration.organizations[0]
            task = db.Task(
                name=f"Example task",
                image=image,
                collaboration=collaboration,
                run_id=db.Task.next_run_id(),
                initiator=initiator
            )

            for organization in collaboration.organizations:
                result = db.Result(
                    task=task,
                    input="something",
                    organization=organization
                )
                result.save()

            task.save()
            log.debug(f"Processed task {task.name}")
