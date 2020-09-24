# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/recover'
"""
from __future__ import print_function, unicode_literals

import logging
import datetime

from flask import request, jsonify, g, render_template
from flask_restful import Resource
from flask_jwt_extended import (
    create_access_token,
    decode_token
)
from jwt.exceptions import DecodeError
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path
from sqlalchemy.orm.exc import NoResultFound

from vantage6 import server
from vantage6.server import db
from vantage6.server.mail_service import send_email
from vantage6.server.resource import with_node, only_for

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        ResetPassword,
        path+'/reset',
        endpoint="reset_password",
        methods=('POST',)
    )

    api.add_resource(
        RecoverPassword,
        path+'/lost',
        endpoint='recover_password',
        methods=('POST',)
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class ResetPassword(Resource):
    """user can use recover token to reset their password."""

    @swag_from(str(Path(r"swagger/post_reset_password.yaml")),
               endpoint='reset_password')
    def post(self):
        """"submit email-adress receive token."""

        # retrieve user based on email or username
        body = request.get_json()
        reset_token = body.get("reset_token")
        password = body.get("password")

        if not reset_token or not password:
            return {"msg": "reset token and/or password is missing!"}, \
                HTTPStatus.BAD_REQUEST

        # obtain user
        try:
            user_id = decode_token(reset_token)['identity'].get('id')
        except DecodeError:
            return {"msg": "Invalid recovery token!"}, HTTPStatus.BAD_REQUEST

        log.debug(user_id)
        user = db.User.get(user_id)
        log.debug(user.username)

        # set password
        user.set_password(password)
        user.save()

        log.info(f"Successfull password reset for '{user.username}'")
        return {"msg": "password successfully been reset!"}, \
            HTTPStatus.OK


class RecoverPassword(Resource):
    """send a mail containing a recover token"""

    @swag_from(str(Path(r"swagger/post_recover_password.yaml")),
               endpoint='recover_password')
    def post(self):
        """username or email generates a token which is mailed."""

        # default return string
        ret = {"msg": "If the username or email is our database you "
                      "will soon receive an email"}

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

        send_email(
            "password reset",
            sender="support@vantage6.ai",
            recipients=[user.email],
            text_body=render_template("mail/reset_password.txt",
                                      token=reset_token),
            html_body=render_template("mail/reset_password.html",
                                      token=reset_token)
        )

        return ret
