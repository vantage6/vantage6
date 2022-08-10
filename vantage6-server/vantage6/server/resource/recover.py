# -*- coding: utf-8 -*-
import logging
import datetime

from flask import request, render_template, g
from flask_jwt_extended import (
    create_access_token,
    decode_token
)
from jwt.exceptions import DecodeError
from http import HTTPStatus
from sqlalchemy.orm.exc import NoResultFound
import uuid

from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.resource import ServicesResources, with_user

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        ResetPassword,
        path+'/reset',
        endpoint="reset_password",
        methods=('POST',),
        resource_class_kwargs=services
    )

    api.add_resource(
        RecoverPassword,
        path+'/lost',
        endpoint='recover_password',
        methods=('POST',),
        resource_class_kwargs=services
    )

    api.add_resource(
        ChangePassword,
        api_base+'/password/change',
        endpoint='change_password',
        methods=('PATCH',),
        resource_class_kwargs=services
    )

    api.add_resource(
        ResetAPIKey,
        path+'/node',
        endpoint="reset_api_key",
        methods=('POST',),
        resource_class_kwargs=services
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class ResetPassword(ServicesResources):
    """user can use recover token to reset their password."""

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

        tags: ["Password recovery"]
        """
        # retrieve user based on email or username
        body = request.get_json()
        reset_token = body.get("reset_token")
        password = body.get("password")

        if not reset_token or not password:
            return {"msg": "The reset token and/or password is missing!"}, \
                HTTPStatus.BAD_REQUEST

        # obtain user
        try:
            user_id = decode_token(reset_token)['sub'].get('id')
        except DecodeError:
            return {"msg": "Invalid recovery token!"}, HTTPStatus.BAD_REQUEST

        log.debug(user_id)
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
        return {"msg": "The password has successfully been reset!"}, \
            HTTPStatus.OK


class RecoverPassword(ServicesResources):
    """send a mail containing a recover token"""

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
                    description: Username from which the password needs to be
                      recovered

        responses:
          200:
            description: Ok
          400:
            description: No username or email provided

        tags: ["Password recovery"]
        """
        # default return string
        ret = {"msg": "If the username or email is in our database you "
                      "will soon receive an email."}

        # obtain username/email from request'
        body = request.get_json()
        username = body.get("username")
        email = body.get("email")
        if not (email or username):
            return {"msg": "No username or email provided!"}, \
                HTTPStatus.BAD_REQUEST

        # find user in the database, if not here we stop!
        try:
            if username:
                user = db.User.get_by_username(username)
            else:
                user = db.User.get_by_email(email)
        except NoResultFound:
            # we do not tell them.... But we won't continue either
            return ret

        log.info(f"Password reset requested for '{user.username}'")

        # generate a token that can reset their password
        expires = datetime.timedelta(hours=1)
        reset_token = create_access_token(
            {"id": str(user.id)}, expires_delta=expires
        )

        self.mail.send_email(
            "password reset",
            sender="support@vantage6.ai",
            recipients=[user.email],
            text_body=render_template("mail/reset_password_token.txt",
                                      token=reset_token),
            html_body=render_template("mail/reset_password_token.html",
                                      token=reset_token)
        )

        return ret


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

        tags: ["Password recovery"]
        """
        body = request.get_json()
        old_password = body.get("current_password")
        new_password = body.get("new_password")

        if not old_password:
            return {"msg": "Your current password is missing"},  \
                HTTPStatus.BAD_REQUEST
        elif not new_password:
            return {"msg": "Your new password is missing!"}, \
                HTTPStatus.BAD_REQUEST

        user = g.user
        log.debug(f"Changing password for user {user.id}")

        # check if the old password is correct
        pw_correct = user.check_password(old_password)
        if not pw_correct:
            return {"msg": "Your current password is not correct!"}, \
                HTTPStatus.UNAUTHORIZED

        if old_password == new_password:
            return {"msg": "New password is the same as current password!"}, \
                HTTPStatus.BAD_REQUEST

        # set password
        msg = user.set_password(new_password)
        if msg:
            return {"msg": msg}, HTTPStatus.BAD_REQUEST

        log.info(f"Successful password change for '{user.username}'")
        return {"msg": "The password has been changed successfully!"}, \
            HTTPStatus.OK


class ResetAPIKey(ServicesResources):
    """User can reset API key."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)

        # obtain permissions to check if user is allowed to modify nodes
        self.r = getattr(self.permissions, 'node')

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
                    type: int
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

        tags: ["Password recovery"]
        """
        if not request.is_json:
            log.warning('Authentication failed because no JSON body was '
                        'provided!')
            return {"msg": "Missing JSON in request"}, HTTPStatus.BAD_REQUEST

        # check which node should have its API key modified
        id = request.json.get('id', None)
        if not id:
            msg = "ID missing in JSON body"
            log.error(msg)
            return {"msg": msg}, HTTPStatus.BAD_REQUEST

        # find the node
        node = db.Node.get(id)
        if not node:
            return {'msg': f'Node id={id} is not found!'}, HTTPStatus.NOT_FOUND

        # check if user is allowed to edit the node
        if not self.r.e_glo.can():
            own = g.user.organization.id == node.organization.id
            if not (self.r.e_org.can() and own):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # all good, change API key
        log.info(f"Successful API key reset for node {id}")
        api_key = str(uuid.uuid1())
        node.api_key = api_key
        node.save()

        return {"api_key": api_key}, HTTPStatus.OK
