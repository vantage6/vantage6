import logging
from functools import wraps
from http import HTTPStatus
from typing import Any, List
from sqlalchemy import or_

from requests import Session

from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class UnauthorizedError(Exception):
    def __init__(self, message):
        self.message = message
        self.status_code = HTTPStatus.UNAUTHORIZED


class NotFoundError(Exception):
    def __init__(self, message):
        self.message = message
        self.status_code = HTTPStatus.NOT_FOUND


class BadRequestError(Exception):
    def __init__(self, message):
        self.message = message
        self.status_code = HTTPStatus.BAD_REQUEST


def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        log.debug(f"Handling exceptions for {func.__name__}")
        try:
            return func(*args, **kwargs)
        except UnauthorizedError as e:
            return {"msg": e.message}, e.status_code
        except NotFoundError as e:
            return {"msg": e.message}, e.status_code
        except BadRequestError as e:
            return {"msg": e.message}, e.status_code
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

    return wrapper


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


def filter_by_name_or_description(db, query, args):
    for param in ["name", "description"]:
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
