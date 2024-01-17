import sys
import logging
import datetime as dt
import pyotp

from http import HTTPStatus
from flask import request, render_template, current_app, Flask
from flask_mail import Mail
from threading import Thread

from vantage6.common.globals import APPNAME, MAIN_VERSION_NAME
from vantage6.server.globals import (
    DEFAULT_SUPPORT_EMAIL_ADDRESS, DEFAULT_MAX_FAILED_ATTEMPTS,
    DEFAULT_INACTIVATION_MINUTES, DEFAULT_BETWEEN_BLOCKED_LOGIN_EMAIL_MINUTES
)
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
    log.info("Trying to login '%s'", username)
    failed_login_msg = "Failed to login"

    # check if username exists. If it does not, we continue anyway, to prevent
    # that an attacker can find out which usernames exist via a timing attack.
    username_exists = User.username_exists(username)
    random_username = User.get_first_user().username
    user = User.get_by_username(username) if username_exists \
        else User.get_by_username(random_username)

    password_policy = config.get("password_policy", {})
    max_failed_attempts = password_policy.get(
        'max_failed_attempts', DEFAULT_MAX_FAILED_ATTEMPTS
    )
    inactivation_time = password_policy.get(
        'inactivation_minutes', DEFAULT_INACTIVATION_MINUTES
    )
    minutes_between_blocked_emails = password_policy.get(
        'between_email_blocked_login_minutes',
        DEFAULT_BETWEEN_BLOCKED_LOGIN_EMAIL_MINUTES
    )

    is_blocked, min_rem = user.is_blocked(max_failed_attempts,
                                          inactivation_time)

    # check if the user has already been sent an email in the last hour - in
    # case may want to we send them one, we don't want to spam them
    email_sent_recently = user.last_email_failed_login_sent and (
        dt.datetime.now() < user.last_email_failed_login_sent +
        dt.timedelta(minutes=minutes_between_blocked_emails)
    )

    if user.check_password(password) and not is_blocked and username_exists:
        # Note: above the username_exists is checked to prevent that an
        # attacker happens to get the correct password for the random user
        # that is returned when the username does not exist. Note also that
        # the password is checked first to keep the timing equal for both.
        user.failed_login_attempts = 0
        user.save()
        return user, HTTPStatus.OK
    else:
        # update the number of failed login attempts
        if not username_exists:
            # As the username does not exist or user is blocked, do not
            # update the number of failed login attempts here.
            pass
        elif is_blocked:
            # If the user is blocked, do not update the number of failed login
            # attempts here, but if we are going to send them an email, update
            # the database to reflect that (this is done here rather than in
            # the subthread since that DB updates don't work there)
            if not email_sent_recently:
                user.last_email_failed_login_sent = dt.datetime.now()
        elif (
            not user.failed_login_attempts or
            user.failed_login_attempts >= max_failed_attempts
        ):
            user.failed_login_attempts = 1
            user.last_login_attempt = dt.datetime.now()
        else:
            user.failed_login_attempts += 1
            user.last_login_attempt = dt.datetime.now()
        # Always save the user object to keep timing similar in all cases.
        user.save()

    # Start a separate thread to send an email to the user if the user is
    # blocked. This is done in a separate thread to keep response times similar
    # in all cases.
    # pylint: disable=W0212
    t = Thread(target=__notify_user_blocked, args=(
        current_app._get_current_object(), is_blocked and username_exists,
        user, max_failed_attempts, min_rem, mail, config,
        request.access_route[-1], email_sent_recently
    ))
    t.start()

    return {"msg": failed_login_msg}, HTTPStatus.UNAUTHORIZED


def __notify_user_blocked(
    app: Flask, is_blocked: bool, user: User, max_n_attempts: int,
    min_rem: int, mail: Mail, config: dict, ip: str, email_sent_recently
) -> None:
    """
    Sends an email to the user when his or her account is locked

    Note that this function is called in a separate thread to keep response
    times for login attempts similar in all cases. Therefore, this function
    calls `sys.exit()` to terminate the thread.

    Parameters
    ----------
    current_app: flask.Flask
        The current Flask app
    is_blocked: bool
        Whether or not the user is blocked
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
    ip: str
        IP address from where the login attempt was made
    email_sent_recently: bool
        Whether or not the user has been sent an email so recently that we do
        not want to send them another one
    """
    if not is_blocked or email_sent_recently:
        sys.exit()

    log.info('User %s is locked. Sending them an email.', user.username)

    email_info = config.get("smtp", {})
    email_sender = email_info.get("username", DEFAULT_SUPPORT_EMAIL_ADDRESS)
    support_email = config.get("support_email", email_sender)

    template_vars = {
        'firstname': user.firstname if user.firstname else user.username,
        'number_of_allowed_attempts': max_n_attempts,
        'ip': ip,
        'time': dt.datetime.now(dt.timezone.utc),
        'time_remaining': min_rem,
        'support_email': support_email,
    }

    with app.app_context():
        mail.send_email(
            "Failed login attempts on your vantage6 account",
            sender=email_sender,
            recipients=[user.email],
            text_body=render_template(
                "mail/blocked_account.txt", **template_vars
            ),
            html_body=render_template(
                "mail/blocked_account.html", **template_vars
            )
        )
    sys.exit()


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
