import logging
import datetime as dt
import pyotp

from http import HTTPStatus
from typing import Dict, Tuple, Union

from vantage6.common.globals import APPNAME
from vantage6.server.globals import DEFAULT_SUPPORT_EMAIL_ADDRESS
from vantage6.server import db
from vantage6.server.model.user import User

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def user_login(
    password_policy: Dict, username: str, password: str
) -> Tuple[Union[User, Dict], HTTPStatus]:
    """
    Returns user a message in case of failed login attempt.

    config: ConfigurationManager
        An instance of a vantage6 configuration manager for a vantage6 server
    username: str
        Username of user to be logged in
    password: str
        Password of user to be logged in

    Returns
    -------
    User or Dict:
        User SQLAlchemy model if user is logged in, otherwise dictionary with
        error message
    HTTPStatus:
        Status code that the current request should return
    """
    log.info(f"Trying to login '{username}'")

    if db.User.username_exists(username):
        user = db.User.get_by_username(username)
        max_failed_attempts = password_policy.get('max_failed_attempts', 5)
        inactivation_time = password_policy.get('inactivation_minutes', 15)

        is_blocked, time_remaining_msg = user.is_blocked(
            max_failed_attempts, inactivation_time)
        if is_blocked:
            return {"msg": time_remaining_msg}, HTTPStatus.UNAUTHORIZED
        elif user.check_password(password):
            user.failed_login_attempts = 0
            user.save()
            return user, HTTPStatus.OK
        else:
            # update the number of failed login attempts
            user.failed_login_attempts = 1 \
                if (
                    not user.failed_login_attempts or
                    user.failed_login_attempts >= max_failed_attempts
                ) else user.failed_login_attempts + 1
            user.last_login_attempt = dt.datetime.now()
            user.save()

    return {"msg": "Invalid username or password!"}, \
        HTTPStatus.UNAUTHORIZED


def create_qr_uri(smtp_config, user) -> Dict:
    """
    Create the URI to generate a QR code for authenticator apps

    Parameters
    ----------
    config: ConfigurationManager
        An instance of a vantage6 configuration manager for a vantage6 server
    user: User
        User for whom two-factor authentication is to be set up

    Returns
    -------
    Dict
        Dictionary with information on the TOTP secret required to generate
        a QR code or to enter it manually in an authenticator app
    """
    provision_email = smtp_config.get("username",
                                      DEFAULT_SUPPORT_EMAIL_ADDRESS)
    otp_secret = pyotp.random_base32()
    qr_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(
        name=provision_email, issuer_name=APPNAME
    )
    user.otp_secret = otp_secret
    user.save()
    return {
        'qr_uri': qr_uri,
        'otp_secret': otp_secret,
        'msg': ('Two-factor authentication is obligatory on this server. '
                'Please visualize the QR code to set up authentication.')
    }
