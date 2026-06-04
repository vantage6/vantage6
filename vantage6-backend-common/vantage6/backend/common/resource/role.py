import logging
from typing import Any, List

from requests import Session
from sqlalchemy import or_

from vantage6.common import logger_name

from vantage6.backend.common.permission import PermissionManagerBase
from vantage6.backend.common.resource.error_handling import (
    BadRequestError,
    NotFoundError,
)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def validate_request_body(schema, data, partial=False):
    errors = schema.validate(data, partial=partial)
    if errors:
        raise BadRequestError(errors)
    return None


def get_rules(data: Any, db: Session) -> List:
    rules = []
    if data["rules"]:
        for rule_id in data["rules"]:
            rule = db.Rule.get(rule_id)
            if not rule:
                raise NotFoundError(f"Rule with id {rule_id} not found")
            rules.append(rule)
    return rules


def filter_by_attribute(db, params: list, query, args):
    for param in params:
        filters = args.getlist(param)
        if filters:
            query = query.filter(
                or_(*[getattr(db.Role, param).like(f) for f in filters])
            )
    return query


def validate_user_exists(db, user_id):
    user = db.User.get(user_id)
    if not user:
        raise BadRequestError(f"User with id={user_id} does not exist!")
    return user


def apply_user_filter(db, query, user_id):
    return query.join(db.Permission).join(db.User).filter(db.User.id == user_id)


def get_role(db, role_id):
    role = db.Role.get(role_id)
    if not role:
        raise NotFoundError(f"Role with id={role_id} not found.")
    return role


def check_default_role(role, default_roles):
    if role.name in default_roles:
        raise BadRequestError(
            f"Role {role.name} is a default role and cannot be edited or deleted."
        )


def get_rule(db, rule_id):
    rule = db.Rule.get(rule_id)
    if not rule:
        raise NotFoundError(f"Rule with id={rule_id} not found.")
    return rule


def get_rules_from_ids(rule_ids, db):
    rules = []
    for rule_id in rule_ids:
        rule = get_rule(db, rule_id)
        rules.append(rule)
    return rules


def update_role(role, data, db, permissions: PermissionManagerBase):
    if "name" in data:
        role.name = data["name"]
    if "description" in data:
        role.description = data["description"]
    if "rules" in data:
        rules = get_rules_from_ids(data["rules"], db)
        permissions.check_user_rules(rules)
        role.rules = rules
    return role


def can_delete_dependents(role, delete_dependents):
    if role.users:
        if delete_dependents:
            log.warn(
                f"Role {id} will be deleted even though it was assigned to users. This may result in missing permissions."
            )
        else:
            raise BadRequestError(
                f"Role {role.name} is assigned to users and cannot be deleted."
            )
