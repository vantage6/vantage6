from flask import g

from vantage6.server import db


def obtain_auth_collaborations() -> list[db.Collaboration]:
    """
    Obtain the collaborations that the auth is part of.

    Returns
    -------
    list[db.Collaboration]
        List of collaborations
    """
    if g.user:
        return g.user.organization.collaborations
    elif g.node:
        return g.node.organization.collaborations
    else:
        return [db.Collaboration.get(g.container["collaboration_id"])]


def obtain_auth_organization() -> db.Organization:
    """
    Obtain the organization model from the auth that is logged in.

    Returns
    -------
    db.Organization
        Organization model
    """
    if g.user:
        org_id = g.user.organization.id
    elif g.node:
        org_id = g.node.organization.id
    else:
        org_id = g.container["organization_id"]
    return db.Organization.get(org_id)
