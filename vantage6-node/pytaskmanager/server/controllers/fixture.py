import uuid
import logging

from pytaskmanager.server import db

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

def load(ctx, fixtures, drop_all=True):

    uri = ctx.get_database_uri()
    db.init(uri, drop_all=drop_all)

    log.info("Create Organizations and Users")
    for org in fixtures.get("organizations", {}):
        
        # create organization
        organization = db.Organization(**{k:org[k] for k in ["name", "domain",\
            "address1", "address2", "zipcode", "country"]})
        organization.save()
        log.debug(f"processed organization={organization.name}")

        # create users
        for usr in org.get("users",{}):
            user = db.User(**usr)
            user.organization_id=organization.id
            user.save()
            log.debug(f"processed user={user.username}")

    log.info("Create collaborations")
    for col in fixtures.get("collaborations",{}):
        
        # create collaboration 
        collaboration = db.Collaboration(name=col.get("name"))
        log.debug(f"processed collaboration={collaboration.name}")

        # append organizations to the collaboration
        for name in col.get("participants",{}): 
            collaboration.organizations.append(
                db.Organization.get_by_name(name)
            )
            log.debug(f"added {name} to the collaboration")
        collaboration.save()

        # append dummy tasks to the collaboration
        for image in col.get("tasks",{}):
            task = db.Task(
                name=f"Example task",
                image=image,
                collaboration=collaboration
            )
            task.save()
            log.debug(f"Processed task {task.name}")

