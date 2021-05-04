import uuid
import logging

import vantage6.server.model as db
from vantage6.server.model.base import Database

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def load(fixtures, drop_all=False):
    # TODO we are not sure the DB is connected here....

    if drop_all:
        Database().drop_all()

    log.info("Create Organizations and Users")
    for org in fixtures.get("organizations", {}):

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

            if isinstance(participant, str):
                org_name = participant
                node_api_key = str(uuid.uuid1())
            else:  # == isinstance(participant, dict):
                org_name = participant.get("name")
                node_api_key = participant.get("api-key", str(uuid.uuid1()))

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
