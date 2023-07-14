import logging
import datetime as dt
import pyotp

from http import HTTPStatus
from flask import request, render_template
from flask_mail import Mail

from vantage6.common.globals import APPNAME, MAIN_VERSION_NAME
from vantage6.server.globals import DEFAULT_SUPPORT_EMAIL_ADDRESS
from vantage6.server.model.user import User

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def user_login(
    config: dict, username: str, password: str, mail: Mail
) -> tuple[dict | User, HTTPStatus]:
    """
    Returns user a message in case of failed login attempt.

    config: dict
        Dictionary with configuration settings
    username: str
        Username of user to be logged in
    password: str
        Password of user to be logged in
    mail: flask_mail.Mail
        An instance of the Flask mail class. Used to send email to user in case
        of too many failed login attempts.

    Returns
    -------
    :class:`~vantage6.server.model.user.User` or dict:
        User SQLAlchemy model if user is logged in, otherwise dictionary with
        error message
    HTTPStatus:
        Status code that the current request should return
    """
    log.info(f"Trying to login '{username}'")
    failed_login_msg = "Failed to login"
    if User.username_exists(username):
        user = User.get_by_username(username)
        password_policy = config.get("password_policy", {})
        max_failed_attempts = password_policy.get('max_failed_attempts', 5)
        inactivation_time = password_policy.get('inactivation_minutes', 15)

        is_blocked, min_rem = user.is_blocked(max_failed_attempts,
                                              inactivation_time)
        if is_blocked:
            notify_user_blocked(user, max_failed_attempts, min_rem, mail,
                                config)
            return {"msg": failed_login_msg}, HTTPStatus.UNAUTHORIZED
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

    return {"msg": failed_login_msg}, HTTPStatus.UNAUTHORIZED


def notify_user_blocked(
    user: User, max_n_attempts: int, min_rem: int, mail: Mail,
    config: dict
) -> None:
    """
    Sends an email to the user when his or her account is locked

    Parameters
    ----------
    user: :class:`~vantage6.server.model.user.User`
        User who is temporarily blocked
    max_n_attempts: int
        Maximum number of failed login attempts before the account is locked
    min_rem: int
        Number of minutes remaining before the account is unlocked
    mail: flask_mail.Mail
        An instance of the Flask mail class. Used to send email to user in case
        of too many failed login attempts.
    config: dict
        Dictionary with configuration settings
    """
    if not user.email:
        log.warning(f'User {user.username} is locked, but does not have'
                    'an email registered. So no message has been sent.')

    log.info(f'User {user.username} is locked. Sending them an email.')

    email_info = config.get("smtp", {})
    email_sender = email_info.get("username", DEFAULT_SUPPORT_EMAIL_ADDRESS)
    support_email = config.get("support_email", email_sender)

    template_vars = {
        'firstname': user.firstname,
        'number_of_allowed_attempts': max_n_attempts,
        'ip': request.access_route[-1],
        'time': dt.datetime.now(dt.timezone.utc),
        'time_remaining': min_rem,
        'support_email': support_email,
    }

    mail.send_email(
        "Failed login attempts on your vantage6 account",
        sender=email_sender,
        recipients=[user.email],
        text_body=render_template("mail/blocked_account.txt", **template_vars),
        html_body=render_template("mail/blocked_account.html", **template_vars)
    )


def create_qr_uri(user: User) -> dict:
    """
    Create the URI to generate a QR code for authenticator apps

    Parameters
    ----------
    user: :class:`~vantage6.server.model.user.User`
        User for whom two-factor authentication is to be set up

    Returns
    -------
    dict
        Dictionary with information on the TOTP secret required to generate
        a QR code or to enter it manually in an authenticator app
    """
    otp_secret = pyotp.random_base32()
    qr_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(
        name=user.username, issuer_name=f"{APPNAME} ({MAIN_VERSION_NAME})"
    )
    user.otp_secret = otp_secret
    user.save()
    return {
        'qr_uri': qr_uri,
        'otp_secret': otp_secret,
        'msg': ('Two-factor authentication is obligatory on this server. '
                'Please visualize the QR code to set up authentication.')
    }
