import sys
import logging
import datetime as dt
import pyotp

from http import HTTPStatus
from flask import request, render_template, current_app, Flask
from flask_mail import Mail
from threading import Thread

from vantage6.common.globals import APPNAME
from vantage6.backend.common.globals import (
    DEFAULT_EMAIL_FROM_ADDRESS,
    DEFAULT_SUPPORT_EMAIL_ADDRESS,
)
from vantage6.server.globals import (
    DEFAULT_MAX_FAILED_ATTEMPTS,
    DEFAULT_INACTIVATION_MINUTES,
    DEFAULT_BETWEEN_USER_EMAILS_MINUTES,
)
from vantage6.server.model.user import User

module_name = __name__.split(".")[-1]
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
    log.info("Trying to login '%s'", username)
    failed_login_msg = "Failed to login"

    # check if username exists. If it does not, we continue anyway, to prevent
    # that an attacker can find out which usernames exist via a timing attack.
    # In that case, we fetch the first user as random user.
    username_exists = User.username_exists(username)
    random_username = User.get_first_user().username
    user = (
        User.get_by_username(username)
        if username_exists
        else User.get_by_username(random_username)
    )

    password_policy = config.get("password_policy", {})
    max_failed_attempts = password_policy.get(
        "max_failed_attempts", DEFAULT_MAX_FAILED_ATTEMPTS
    )
    inactivation_time = password_policy.get(
        "inactivation_minutes", DEFAULT_INACTIVATION_MINUTES
    )

    is_blocked, min_rem = user.is_blocked(max_failed_attempts, inactivation_time)

    if user.check_password(password) and not is_blocked and username_exists:
        # Note: above the username_exists is checked to prevent that an
        # attacker happens to get the correct password for the random user
        # that is returned when the username does not exist. Note also that
        # the password is checked first to keep the timing equal for both.
        user.failed_login_attempts = 0
        user.save()
        return user, HTTPStatus.OK

    # Handle database updates required upon failed login in a separate thread
    # to ensure similar response times
    # pylint: disable=W0212
    t1 = Thread(
        target=__handle_failed_login,
        args=(
            current_app._get_current_object(),
            username_exists,
            username,
            password_policy,
            is_blocked,
            min_rem,
            mail,
            config,
            request.access_route[-1],
        ),
    )
    t1.start()

    return {"msg": failed_login_msg}, HTTPStatus.UNAUTHORIZED


def __handle_failed_login(
    app: Flask,
    user_exists: bool,
    username: str,
    password_policy: dict,
    is_blocked: bool,
    min_rem: int,
    mail: Mail,
    config: dict,
    ip: str,
) -> None:
    """
    When a user login fails, this function is called to update the database
    with the failed login attempt and send an email to the user if necessary.

    Note that this function is called in a separate thread to keep response
    times for login attempts similar in all cases. Therefore, this function
    calls `sys.exit()` to terminate the thread.

    Parameters
    ----------
    app: flask.Flask
        The current Flask app
    user_exists: bool
        Whether user exists or not
    username: str
        Username of the user that failed to login
    password_policy: dict
        Dictionary with password policy settings.
    min_rem: int
        Number of minutes remaining before the account is unlocked
    mail: flask_mail.Mail
        An instance of the Flask mail class. Used to send email to user in case
        of too many failed login attempts.
    config: dict
        Dictionary with configuration settings
    ip: str
        IP address from where the login attempt was made
    """
    if not user_exists:
        sys.exit()
    # get user object again (required because we are in a new thread)
    user = User.get_by_username(username)

    max_failed_attempts = password_policy.get(
        "max_failed_attempts", DEFAULT_MAX_FAILED_ATTEMPTS
    )

    if is_blocked:
        # alert the user via email that they are blocked
        __notify_user_blocked(app, user, min_rem, mail, config, ip)
        sys.exit()
    elif (
        not user.failed_login_attempts
        or user.failed_login_attempts >= max_failed_attempts
    ):
        # set failed login attempts to 1 if first failed login attempt or if
        # user got unblocked after being blocked previously
        user.failed_login_attempts = 1
    else:
        user.failed_login_attempts += 1
    user.last_login_attempt = dt.datetime.now(dt.timezone.utc)
    user.save()
    sys.exit()


def __notify_user_blocked(
    app: Flask, user: User, min_rem: int, mail: Mail, config: dict, ip: str
) -> None:
    """
    Sends an email to the user when their account is locked.

    This function also checks that emails are not sent too often to the same
    user.

    Parameters
    ----------
    app: flask.Flask
        The current Flask app
    user: :class:`~vantage6.server.model.user.User`
        User who is temporarily blocked
    min_rem: int
        Number of minutes remaining before the account is unlocked
    mail: flask_mail.Mail
        An instance of the Flask mail class. Used to send email to user in case
        of too many failed login attempts.
    config: dict
        Dictionary with configuration settings
    ip: str
        IP address from where the login attempt was made
    """
    log.info("User %s is locked. Sending them an email.", user.username)

    # check that email has not already been sent recently
    password_policy = config.get("password_policy", {})
    minutes_between_blocked_emails = password_policy.get(
        "between_user_emails_minutes",
        DEFAULT_BETWEEN_USER_EMAILS_MINUTES,
    )
    email_sent_recently = user.last_email_failed_login_sent and (
        dt.datetime.now(dt.timezone.utc)
        < user.last_email_failed_login_sent
        + dt.timedelta(minutes=minutes_between_blocked_emails)
    )
    if email_sent_recently:
        return

    # send email
    smtp_settings = config.get("smtp", {})
    email_from = smtp_settings.get("email_from", DEFAULT_EMAIL_FROM_ADDRESS)
    support_email = config.get("support_email", DEFAULT_SUPPORT_EMAIL_ADDRESS)

    max_failed_attempts = password_policy.get(
        "max_failed_attempts", DEFAULT_MAX_FAILED_ATTEMPTS
    )
    template_vars = {
        "firstname": user.firstname if user.firstname else user.username,
        "number_of_allowed_attempts": max_failed_attempts,
        "ip": ip,
        "time": dt.datetime.now(dt.timezone.utc),
        "time_remaining": min_rem,
        "support_email": support_email,
    }

    with app.app_context():
        mail.send_email(
            "Failed login attempts on your vantage6 account",
            sender=email_from,
            recipients=[user.email],
            text_body=render_template("mail/blocked_account.txt", **template_vars),
            html_body=render_template("mail/blocked_account.html", **template_vars),
        )

    # Update latest email sent timestamp
    user.last_email_failed_login_sent = dt.datetime.now(dt.timezone.utc)
    user.save()


def create_qr_uri(user: User, server_name: str) -> dict:
    """
    Create the URI to generate a QR code for authenticator apps

    Parameters
    ----------
    user: :class:`~vantage6.server.model.user.User`
        User for whom two-factor authentication is to be set up
    server_name: str
        Name of the server. This is used in the issuer name in the URI

    Returns
    -------
    dict
        Dictionary with information on the TOTP secret required to generate
        a QR code or to enter it manually in an authenticator app
    """
    otp_secret = pyotp.random_base32()
    qr_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(
        name=user.username, issuer_name=f"{APPNAME} ({server_name})"
    )
    user.otp_secret = otp_secret
    user.save()
    return {
        "qr_uri": qr_uri,
        "otp_secret": otp_secret,
        "msg": (
            "Two-factor authentication is obligatory on this server. "
            "Please visualize the QR code to set up authentication."
        ),
    }
