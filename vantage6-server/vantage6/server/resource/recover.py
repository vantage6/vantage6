import logging
import datetime as dt
from http import HTTPStatus

import gevent
from flask import request, render_template, g, current_app, Flask
from flask_jwt_extended import create_access_token, decode_token
from flask_restful import Api
from flask_mail import Mail
from marshmallow import ValidationError
from jwt.exceptions import DecodeError
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common import logger_name, generate_apikey
from vantage6.common.globals import APPNAME, MAIN_VERSION_NAME
from vantage6.backend.common.globals import (
    DEFAULT_EMAIL_FROM_ADDRESS,
    DEFAULT_SUPPORT_EMAIL_ADDRESS,
)
from vantage6.server import db
from vantage6.server.globals import (
    DEFAULT_EMAILED_TOKEN_VALIDITY_MINUTES,
    DEFAULT_BETWEEN_USER_EMAILS_MINUTES,
)
from vantage6.server.model.rule import Operation
from vantage6.server.resource import ServicesResources, with_user
from vantage6.server.resource.common.auth_helper import create_qr_uri, user_login
from vantage6.server.resource.common.input_schema import (
    ChangePasswordInputSchema,
    RecoverPasswordInputSchema,
    ResetPasswordInputSchema,
    Recover2FAInputSchema,
    Reset2FAInputSchema,
    ResetAPIKeyInputSchema,
)
from vantage6.server.model.user import User

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the recover resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api
    services : dict
        Dictionary with services required for the resource endpoints
    """
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        ResetPassword,
        path + "/reset",
        endpoint="reset_password",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        RecoverPassword,
        path + "/lost",
        endpoint="recover_password",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        ResetTwoFactorSecret,
        path + "/2fa/reset",
        endpoint="reset_2fa_secret",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        RecoverTwoFactorSecret,
        path + "/2fa/lost",
        endpoint="recover_2fa_secret",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        ChangePassword,
        api_base + "/password/change",
        endpoint="change_password",
        methods=("PATCH",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        ResetAPIKey,
        path + "/node",
        endpoint="reset_api_key",
        methods=("POST",),
        resource_class_kwargs=services,
    )


recover_pw_schema = RecoverPasswordInputSchema()
reset_pw_schema = ResetPasswordInputSchema()
recover_2fa_schema = Recover2FAInputSchema()
reset_2fa_schema = Reset2FAInputSchema()
reset_api_key_schema = ResetAPIKeyInputSchema()
change_pw_schema = ChangePasswordInputSchema()


# used by RecoverPassword.post()
def _handle_password_recovery(
    app: Flask, username: str, email: str, config: dict, mail: Mail
) -> None:
    """
    Send an email to user with a password reset token.

    This function also checks whether such an email has been sent recently, and
    if so avoids sending it.

    Parameters
    ----------
    app: flask.Flask
        The current Flask app
    username: str
        User for who the password reset is being requested
    email: str
        Email address associated to an account for which the password reset is
        being requested
    config: dict
        Dictionary with configuration settings
    mail: flask_mail.Mail
        An instance of the Flask mail class. Used to send email to user in case
        of too many failed login attempts.
    """
    # read settings
    password_policy = config.get("password_policy", {})
    minutes_between_password_reset_emails = password_policy.get(
        "between_user_emails_minutes",
        DEFAULT_BETWEEN_USER_EMAILS_MINUTES,
    )
    smtp_settings = config.get("smtp", {})
    minutes_token_valid = smtp_settings.get(
        "email_token_validity_minutes", DEFAULT_EMAILED_TOKEN_VALIDITY_MINUTES
    )
    expires = dt.timedelta(minutes=minutes_token_valid)
    email_from = smtp_settings.get("email_from", DEFAULT_EMAIL_FROM_ADDRESS)
    support_email = config.get("support_email", DEFAULT_SUPPORT_EMAIL_ADDRESS)

    try:
        user = User.get_by_username(username) if username else User.get_by_email(email)
    except NoResultFound:
        account_name = username or email
        log.info(
            "Someone requested password recovery for non-existing account '%s'",
            account_name,
        )
        return

    log.info("Password reset requested for '%s'", user.username)

    # check that email has not already been sent recently
    email_sent_recently = user.last_email_recover_password_sent and (
        dt.datetime.now(dt.timezone.utc)
        < user.last_email_recover_password_sent
        + dt.timedelta(minutes=minutes_between_password_reset_emails)
    )
    if email_sent_recently:
        log.info("Skipping sending password reset email to '%s'", user.username)
        return

    with app.app_context():
        # generate a token that can reset their password
        reset_token = create_access_token({"id": str(user.id)}, expires_delta=expires)
        log.info("Sending password reset email to '%s'", user.email)
        mail.send_email(
            f"Password reset {APPNAME}",
            sender=email_from,
            recipients=[user.email],
            text_body=render_template(
                "mail/reset_token.txt",
                token=reset_token,
                firstname=user.firstname,
                reset_type="password",
                what_to_do="simply ignore this message",
            ),
            html_body=render_template(
                "mail/reset_token.html",
                token=reset_token,
                firstname=user.firstname,
                reset_type="password",
                support_email=support_email,
                what_to_do="simply ignore this message",
            ),
        )

    # Update last password reset email sent date
    user.last_email_recover_password_sent = dt.datetime.now(dt.timezone.utc)
    user.save()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class ResetPassword(ServicesResources):
    """User can use recover token to reset their password."""

    def post(self):
        """Set a new password using a recover token
        ---
        description: >-
          User can use a recover token to reset their password

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  reset_token:
                    type: string
                    description: Recover token (received by email)
                  password:
                    type: string
                    description: New password

        responses:
          200:
            description: Ok
          400:
            description: Password or recovery token is missing or invalid

        tags: ["Account recovery"]
        """
        body = request.get_json(silent=True)
        # validate request body
        try:
            body = reset_pw_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        reset_token = body.get("reset_token")
        password = body.get("password")

        # obtain user
        try:
            user_id = decode_token(reset_token)["sub"].get("id")
        except DecodeError:
            return {"msg": "Invalid recovery token!"}, HTTPStatus.BAD_REQUEST

        user = db.User.get(user_id)

        # reset number of failed login attempts to prevent that user cannot
        # reactivate via email
        user.failed_login_attempts = 0
        user.save()

        # set password
        msg = user.set_password(password)
        if msg:
            return {"msg": msg}, HTTPStatus.BAD_REQUEST

        log.info(f"Successfull password reset for '{user.username}'")
        return {"msg": "The password has successfully been reset!"}, HTTPStatus.OK


class RecoverPassword(ServicesResources):
    """Send a mail containing a recover token to reset the password"""

    def post(self):
        """Request a recover token
        ---
        description: >-
          Request a recover token if password is lost. Either email address
          or username must be supplied.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  username:
                    type: string
                    description: Username from which the password needs to be
                      recovered
                  email:
                    type: string
                    description: Email of user from which the password needs to
                      be recovered

        responses:
          200:
            description: Ok
          400:
            description: No username or email provided

        tags: ["Account recovery"]
        """
        # default return string
        ret = {
            "msg": "If the username or email is in our database you "
            "will soon receive an email."
        }
        body = request.get_json(silent=True)

        # validate request body
        try:
            body = recover_pw_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # obtain username/email from request
        username = body.get("username")
        email = body.get("email")

        log.debug("Scheduling handling of password recovery request")
        # we schedule _handle_password_recovery in '3' seconds to make it very
        # likely we'll respond to the user's request (HTTP) before we start
        # executing its code. We do this to avoid potential timing attacks
        gevent.spawn_later(
            3,
            _handle_password_recovery,
            current_app._get_current_object(),
            username,
            email,
            self.config,
            self.mail,
        )

        return ret


class ResetTwoFactorSecret(ServicesResources):
    """User can use recover token to reset their two-factor authentication."""

    def post(self):
        """Set a new two-factor authentication secret using a recover token
        ---
        description: >-
          User can use a recover token to reset their two-factor authentication
          secret

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  reset_token:
                    type: string
                    description: Recover token (received by email)

        responses:
          200:
            description: Ok
          400:
            description: Recovery token is missing or invalid

        tags: ["Account recovery"]
        """
        # retrieve user based on email or username
        body = request.get_json(silent=True)

        # validate request body
        try:
            body = reset_2fa_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # obtain user
        reset_token = body.get("reset_token")
        try:
            user_id = decode_token(reset_token)["sub"].get("id")
        except DecodeError:
            return {"msg": "Invalid recovery token!"}, HTTPStatus.BAD_REQUEST

        user = db.User.get(user_id)
        server_name = self.config.get("server_name", MAIN_VERSION_NAME)

        log.info(f"Resetting two-factor authentication for {user.username}")
        return create_qr_uri(user, server_name), HTTPStatus.OK


class RecoverTwoFactorSecret(ServicesResources):
    """Send a mail containing a recover token for the 2fa secret"""

    def post(self):
        """Request a recover token to reset two-factor authentication secret
        ---
        description: >-
          Request a recover token if two-factor authentication secret is lost.
          A password and a username must be supplied.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  username:
                    type: string
                    description: Username from which the 2fa needs to be reset
                  password:
                    type: string
                    description: Password of user whose 2fa needs to be reset

        responses:
          200:
            description: Ok
          400:
            description: No username or email and password provided

        tags: ["Account recovery"]
        """
        # obtain parameters from request
        body = request.get_json(silent=True)

        # validate request body
        try:
            body = recover_2fa_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        username = body.get("username")
        password = body.get("password")

        # check credentials
        user, login_status = user_login(self.config, username, password, self.mail)
        if login_status != HTTPStatus.OK:
            log.error(f"Failed attempt to reset 2FA for submitted user '%s'", username)
            # Note: user_login() returns a dict with an error message if login
            #       failed as first returned element ('user')
            return user, login_status

        log.info(f"2FA reset requested for '{user.username}'")

        # generate a token that can reset their password
        smtp_settings = self.config.get("smtp", {})
        minutes_token_valid = smtp_settings.get(
            "email_token_validity_minutes", DEFAULT_EMAILED_TOKEN_VALIDITY_MINUTES
        )
        expires = dt.timedelta(minutes=minutes_token_valid)
        reset_token = create_access_token({"id": str(user.id)}, expires_delta=expires)

        email_from = smtp_settings.get("email_from", DEFAULT_EMAIL_FROM_ADDRESS)
        support_email = self.config.get("support_email", DEFAULT_SUPPORT_EMAIL_ADDRESS)

        self.mail.send_email(
            f"Two-factor authentication reset {APPNAME}",
            sender=email_from,
            recipients=[user.email],
            text_body=render_template(
                "mail/reset_token.txt",
                token=reset_token,
                firstname=user.firstname,
                reset_type="two-factor authentication code",
                what_to_do=("please reset your password! It has been compromised"),
            ),
            html_body=render_template(
                "mail/reset_token.html",
                token=reset_token,
                firstname=user.firstname,
                reset_type="two-factor authentication code",
                support_email=support_email,
                what_to_do=("please reset your password! It has been compromised"),
            ),
        )
        log.info("2FA reset request email sent for '%s'", user.username)

        return {
            "msg": "You should have received an email that will allow you to reset your 2FA."
        }, login_status


class ChangePassword(ServicesResources):
    """
    Let user change their password with old password as verification
    """

    @with_user
    def patch(self):
        """Set a new password using the current password
        ---
        description: >-
          Users can change their password by submitting their current password
          and a new password

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  current_password:
                    type: string
                    description: current password
                  new_password:
                    type: string
                    description: new password

        responses:
          200:
            description: Ok
          400:
            description: Current or new password is missing from JSON body, or
              they are the same, or the new password doesn't meet password
              criteria
          401:
            description: Current password is incorrect

        tags: ["Account recovery"]
        """
        body = request.get_json(silent=True)
        # validate request body
        try:
            body = change_pw_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        old_password = body.get("current_password")
        new_password = body.get("new_password")

        user = g.user
        log.info(f"Changing password for user {user.id}")

        # check if the old password is correct
        pw_correct = user.check_password(old_password)
        if not pw_correct:
            return {
                "msg": "Your current password is not correct!"
            }, HTTPStatus.UNAUTHORIZED

        if old_password == new_password:
            return {
                "msg": "New password is the same as current password!"
            }, HTTPStatus.BAD_REQUEST

        # set password
        msg = user.set_password(new_password)
        if msg:
            return {"msg": msg}, HTTPStatus.BAD_REQUEST

        log.info(f"Successful password change for '{user.username}'")
        return {"msg": "The password has been changed successfully!"}, HTTPStatus.OK


class ResetAPIKey(ServicesResources):
    """User can reset API key."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)

        # obtain permissions to check if user is allowed to modify nodes
        self.r = getattr(self.permissions, "node")

    @with_user
    def post(self):
        """Reset a node's API key
        ---
        description: >-
            If a node's API key is lost, this route can be used to obtain a new
            API key.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Node|Global|Edit|❌|❌|Reset API key of node specified by id|\n
            |Node|Organization|Edit|❌|❌|Reset API key of node specified by
            id which is part of your organization |\n

            Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: ID of node whose API key is to be reset

        responses:
            200:
                description: Ok
            400:
                description: ID missing from json body
            401:
                description: Unauthorized
            404:
                description: Node not found

        security:
            - bearerAuth: []

        tags: ["Account recovery"]
        """
        body = request.get_json(silent=True)

        # validate request body
        try:
            body = reset_api_key_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        id_ = body["id"]
        node = db.Node.get(id_)
        if not node:
            return {"msg": f"Node id={id_} is not found!"}, HTTPStatus.NOT_FOUND

        # check if user is allowed to edit the node
        if not self.r.can_for_org(Operation.EDIT, node.organization_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # all good, change API key
        log.info(f"Successful API key reset for node {id}")
        api_key = generate_apikey()
        node.api_key = api_key
        node.save()

        return {"api_key": api_key}, HTTPStatus.OK
