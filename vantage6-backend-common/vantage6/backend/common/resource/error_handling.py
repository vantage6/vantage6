import logging
from functools import wraps
from http import HTTPStatus

from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class UnauthorizedError(Exception):
    """
    Exception raised for unauthorized access errors.

    Attributes:
        message (str): Explanation of the error.
        status_code (HTTPStatus): HTTP status code for the error.
    """

    def __init__(self, message):
        self.message = message
        self.status_code = HTTPStatus.UNAUTHORIZED


class NotFoundError(Exception):
    """
    Exception raised for not found errors.

    Attributes:
        message (str): Explanation of the error.
        status_code (HTTPStatus): HTTP status code for the error.
    """

    def __init__(self, message):
        self.message = message
        self.status_code = HTTPStatus.NOT_FOUND


class BadRequestError(Exception):
    """
    Exception raised for bad request errors.

    Attributes:
        message (str): Explanation of the error.
        status_code (HTTPStatus): HTTP status code for the error.
    """

    def __init__(self, message):
        self.message = message
        self.status_code = HTTPStatus.BAD_REQUEST


def handle_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except UnauthorizedError as e:
            return {"msg": e.message}, e.status_code
        except NotFoundError as e:
            return {"msg": e.message}, e.status_code
        except BadRequestError as e:
            return {"msg": e.message}, e.status_code
        except Exception as e:
            log.exception(e)
            return {
                "msg": "An unexpected error occurred: " + str(e)
            }, HTTPStatus.INTERNAL_SERVER_ERROR

    return wrapper
