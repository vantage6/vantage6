from http import HTTPStatus
from typing import Any, List

from requests import Session


def get_rules(data: Any, db: Session) -> List:
    rules = []
    if data["rules"]:
        for rule_id in data["rules"]:
            rule = db.Rule.get(rule_id)
            if not rule:
                return {"msg": f"Rule id={rule_id} not found."}, HTTPStatus.NOT_FOUND
            rules.append(rule)
