from collections import namedtuple


RuleNeed = namedtuple("RuleNeed", ["name", "scope", "operation"])

rules = {}


def register_rule(rule: str, scopes: list, operations: list, description=None):
    """[summary]

    Parameters
    ----------
    rule : [type]
        [description]
    scopes : [type]
        [description]
    operations : [type]
        [description]
    """
    if rule in rules:
        raise Exception("Rule already exists!")

    rules[rule] = (scopes, operations, description)
