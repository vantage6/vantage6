import datetime
import logging
from http import HTTPStatus
from threading import Thread

from flask import Flask, current_app, g, render_template, request
from flask_mail import Mail
from flask_restful import Api
from marshmallow import ValidationError
from sqlalchemy import or_, select

from vantage6.common import logger_name
from vantage6.common.docker.addons import (
    get_digest,
    get_image_name_wo_tag,
    parse_image_name,
)
from vantage6.common.globals import DATAFRAME_MULTIPLE_KEYWORD

from vantage6.backend.common import get_server_url
from vantage6.backend.common.globals import (
    DEFAULT_EMAIL_FROM_ADDRESS,
    DEFAULT_SUPPORT_EMAIL_ADDRESS,
)
from vantage6.backend.common.resource.pagination import Pagination

from vantage6.algorithm.store import db
from vantage6.algorithm.store.model.algorithm import Algorithm as db_Algorithm
from vantage6.algorithm.store.model.allowed_argument_value import AllowedArgumentValue
from vantage6.algorithm.store.model.argument import Argument
from vantage6.algorithm.store.model.common.enums import AlgorithmStatus, ReviewStatus
from vantage6.algorithm.store.model.database import Database
from vantage6.algorithm.store.model.function import Function
from vantage6.algorithm.store.model.rule import Operation
from vantage6.algorithm.store.model.ui_visualization import UIVisualization
from vantage6.algorithm.store.permission import (
    Operation as P,
    PermissionManager,
)

# TODO move to common / refactor
from vantage6.algorithm.store.resource import (
    AlgorithmStoreResources,
    with_permission,
    with_permission_to_view_algorithms,
)
from vantage6.algorithm.store.resource.schema.input_schema import (
    AlgorithmInputSchema,
    AlgorithmPatchInputSchema,
)
from vantage6.algorithm.store.resource.schema.output_schema import AlgorithmOutputSchema

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the version resource.

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
    log.info('Setting up "%s" and subdirectories', path)

    api.add_resource(
        Algorithms,
        path,
        endpoint="algorithm_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )

    api.add_resource(
        Algorithm,
        path + "/<int:id>",
        endpoint="algorithm_with_id",
        methods=("GET", "DELETE", "PATCH"),
        resource_class_kwargs=services,
    )

    api.add_resource(
        AlgorithmInvalidate,
        path + "/<int:id>/invalidate",
        endpoint="algorithm_invalidate",
        methods=("POST",),
        resource_class_kwargs=services,
    )


algorithm_input_post_schema = AlgorithmInputSchema()
algorithm_input_patch_schema = AlgorithmPatchInputSchema()
algorithm_output_schema = AlgorithmOutputSchema()


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------
def permissions(permission_mgr: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """
    add = permission_mgr.appender(module_name)
    add(P.VIEW, description="View any algorithm")
    add(P.CREATE, description="Create a new algorithm")
    add(P.EDIT, description="Edit any algorithm")
    add(P.DELETE, description="Delete any algorithm")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------


class AlgorithmBaseResource(AlgorithmStoreResources):
    """Base class for the algorithm resource"""

    def _get_image_digest(self, image_name: str) -> tuple[str, str]:
        """
        Get the sha256 of the image.

        Parameters
        ----------
        image : str
            Image url

        Returns
        -------
        tuple[str, str | None]
            Tuple with the docker image including tag, and the digest of the image if
            found. If the digest could not be determined, `None` is returned.
        """
        # split image and tag
        try:
            # pylint: disable=unused-variable
            registry, _, tag = parse_image_name(image_name)
            image_wo_tag = get_image_name_wo_tag(image_name)
        except Exception as e:
            raise ValueError(f"Invalid image name: {image_name}") from e

        # if tag is not a digest, set it in the image name
        # TODO v5+ consider including "latest" also in the image name in the database
        # for consistency. This is not possible in v4 due to backwards compatibility
        # with <4.5 where tags were not included unless explicitly provided.
        if not tag.startswith("sha256:") and not tag == "latest":
            image_and_tag = f"{image_wo_tag}:{tag}"
        else:
            image_and_tag = image_wo_tag

        # get the digest of the image.
        digest = get_digest(image_name)

        # If getting digest failed, try to use authentication
        if not digest:
            docker_registries = self.config.get("docker_registries", [])
            registry_user = None
            registry_password = None
            for reg in docker_registries:
                if reg["registry"] == registry:
                    registry_user = reg.get("username")
                    registry_password = reg.get("password")
                    break
            if registry_user and registry_password:
                digest = get_digest(
                    full_image=image_name,
                    registry_username=registry_user,
                    registry_password=registry_password,
                )

        return image_and_tag, digest


class Algorithms(AlgorithmBaseResource):
    """Resource for /algorithm"""

    @with_permission_to_view_algorithms()
    def get(self):
        """List algorithms
        ---
        description: >-
          Return a list of algorithms

          By default, only approved algorithms are returned. To get non-approved
          algorithms, set the 'awaiting_reviewer_assignment', 'under_review' or
          'invalidated' parameter to True.

        parameters:
          - in: query
            name: name
            schema:
              type: string
            description: Filter on algorithm name using the SQL operator LIKE.
          - in: query
            name: display_name
            schema:
              type: string
            description: Filter on algorithm display name using the SQL operator LIKE.
          - in: query
            name: description
            schema:
              type: string
            description: Filter on algorithm description using the SQL operator
              LIKE.
          - in: query
            name: image
            schema:
              type: string
            description: Filter on algorithm image. If no tag is provided, the
              latest tag is assumed.
          - in: query
            name: awaiting_reviewer_assignment
            schema:
              type: boolean
            description: Filter on algorithms that have not been assigned a reviewer
              yet.
          - in: query
            name: under_review
            schema:
              type: boolean
            description: Filter on algorithms that are currently under review.
          - in: query
            name: in_review_process
            schema:
              type: boolean
            description: Filter on algorithms that are in the review process. This
              includes algorithms that are awaiting reviewer assignment or under review
          - in: query
            name: invalidated
            schema:
              type: boolean
            description: Filter on algorithms that have been invalidated. These may be
              algorithms that have been replaced by a newer version or that have been
              rejected in review.
          - in: query
            name: partitioning
            schema:
              type: string
            description: Filter on algorithm partitioning. Can be 'horizontal'
              or 'vertical'.
          - in: query
            name: vantage6_version
            schema:
              type: string
            description: Filter on algorithm vantage6 version using the SQL
              operator LIKE.

        responses:
          200:
            description: OK
          400:
            description: Invalid input
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        q = select(db_Algorithm)

        # filter on properties
        for field in [
            "name",
            "display_name",
            "description",
            "partitioning",
            "vantage6_version",
        ]:
            if (value := request.args.get(field)) is not None:
                q = q.filter(getattr(db_Algorithm, field).like(value))

        awaiting_reviewer_assignment = bool(
            request.args.get("awaiting_reviewer_assignment", False)
        )
        under_review = bool(request.args.get("under_review", False))
        invalidated = bool(request.args.get("invalidated", False))
        in_review_process = bool(request.args.get("in_review_process", False))
        if sum([awaiting_reviewer_assignment, under_review, invalidated]) > 1:
            return {
                "msg": "Only one of 'awaiting_reviewer_assignment', 'under_review' or "
                "'invalidated' may be set to True at a time."
            }, HTTPStatus.BAD_REQUEST
        elif in_review_process and invalidated:
            return {
                "msg": "Only one of 'in_review_process' or 'invalidated' may be set to "
                "True at a time."
            }, HTTPStatus.BAD_REQUEST
        if awaiting_reviewer_assignment:
            q = q.filter(
                db_Algorithm.status == AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT
            )
        elif under_review:
            q = q.filter(db_Algorithm.status == AlgorithmStatus.UNDER_REVIEW)
        elif invalidated:
            q = q.filter(db_Algorithm.invalidated_at.is_not(None))
        elif in_review_process:
            q = q.filter(
                or_(
                    db_Algorithm.status == AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT,
                    db_Algorithm.status == AlgorithmStatus.UNDER_REVIEW,
                )
            )
        else:
            # by default, only approved algorithms are returned
            q = q.filter(db_Algorithm.status == AlgorithmStatus.APPROVED)

        if (full_image := request.args.get("image")) is not None:
            # determine the sha256 of the image, and filter on that. Sort descending
            # to get the latest addition to the store first
            image, digest = self._get_image_digest(full_image)
            if not digest:
                return {
                    "msg": "Image digest could not be determined"
                }, HTTPStatus.BAD_REQUEST
            q = q.filter(db_Algorithm.image == image)
            # TODO at some point there may only be one registration of each algorithm,
            # so this sorting may not be necessary anymore
            q_with_digest = q.filter(db_Algorithm.digest == digest).order_by(
                db_Algorithm.id.desc()
            )

            # if image with that digest does not exist, check if another image with
            # different digest but same name exists. If it does, throw
            # more specific error
            if g.session.scalars(q_with_digest).first():
                q = q_with_digest
            elif not_digest_match := g.session.scalars(q).first():
                return {
                    "msg": f"The image '{image}' that you provided has digest "
                    f"'{digest}'. This algorithm version is not approved by the "
                    "store. The currently approved version of this algorithm has "
                    f"digest '{not_digest_match.digest}'. Please include this digest if"
                    " you want to use that image."
                }, HTTPStatus.BAD_REQUEST

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.Algorithm)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST

        # model serialization
        return self.response(page, algorithm_output_schema)

    @with_permission(module_name, Operation.CREATE)
    def post(self):
        """Create new algorithm
        ---
        description: >-
          Create a new algorithm. The algorithm is not yet active. It is
          created in a draft state. The algorithm can be activated by
          changing the status to 'active'.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Name of the algorithm
                  description:
                    type: string
                    description: Description of the algorithm
                  image:
                    type: string
                    description: Docker image URL
                  partitioning:
                    type: string
                    description: Type of partitioning. Can be 'horizontal' or
                      'vertical'
                  vantage6_version:
                    type: string
                    description: Version of vantage6 that the algorithm is
                      built with / for
                  code_url:
                    type: string
                    description: URL to the algorithm code repository
                  documentation_url:
                    type: string
                    description: URL to the algorithm documentation
                  submission_comments:
                    type: string
                    description: Comments done by the developer to the submission
                  functions:
                    type: array
                    description: List of functions that are available in the
                      algorithm
                    items:
                      properties:
                        name:
                          type: string
                          description: Name of the function
                        display_name:
                          type: string
                          description: Display name of the function
                        description:
                          type: string
                          description: Description of the function
                        step_type:
                          type: string
                          description: Step type of the function. Can be 'data
                            extraction', 'preprocessing', 'federated_compute',
                            'central_compute', or 'postprocessing'
                        standalone:
                          type: boolean
                          description: Whether this function produces useful results
                            when running it by itself
                        databases:
                          type: array
                          description: List of databases that this function
                            uses
                          items:
                            properties:
                              name:
                                type: string
                                description: Name of the database in the
                                  function
                              description:
                                type: string
                                description: Description of the database
                              multiple:
                                type: boolean
                                description: Whether more than one database can be
                                  supplied.
                        arguments:
                          type: array
                          description: List of arguments that this function
                            uses
                          items:
                            properties:
                              name:
                                type: string
                                description: Name of the argument in the
                                  function
                              display_name:
                                type: string
                                description: Display name of the argument
                              description:
                                type: string
                                description: Description of the argument
                              type:
                                type: string
                                description: Type of argument. Can be 'string',
                                  'string_list', 'integer', 'integer_list', 'float',
                                  'float_list', 'boolean', 'json', 'column',
                                  'column_list', 'organization' or 'organization_list'
                              allowed_values:
                                type: array
                                description: An optional list of allowed values for the
                                  argument. If type of the argument is 'string',
                                  the allowed values should be a list of strings, etc.
                                items:
                                  type: string | int | float
                              has_default_value:
                                type: boolean
                                description: Whether the argument has a default
                                  value. If true, the 'default_value' field must be
                                  provided. Default is false.
                              default_value:
                                type: string | int | float | boolean | list | None
                                description: Default value of the argument. The type
                                  should match the 'type' field, e.g. if 'type' is
                                  'integer', 'default_value' should be an integer.
                                  To set an empty (null) default value, use None.
                              conditional_on:
                                type: string
                                description: Name of the argument that this argument
                                  is conditional on.
                              conditional_operator:
                                type: string
                                description: Comparator used for the conditional
                                  argument. Can be one of '==', '!=', '>', '<', '>=',
                                  '<='.
                              conditional_value:
                                type: string
                                description: Value that the argument should be compared
                                  to.
                              is_frontend_only:
                                type: boolean
                                description: Frontend-only arguments are displayed in
                                  the UI, but are not passed to the algorithm. Default
                                  is false.
                        ui_visualizations:
                          type: array
                          description: List of visualizations that are available in
                            the algorithm
                          items:
                            properties:
                              name:
                                type: string
                                description: Name of the visualization
                              description:
                                type: string
                                description: Description of the visualization
                              type:
                                type: string
                                description: Type of visualization.
                              schema:
                                type: object
                                description: Schema that describes the visualization

        responses:
          201:
            description: Algorithm created successfully
          400:
            description: Invalid input
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        data = request.get_json(silent=True)

        # validate the request body
        try:
            data = algorithm_input_post_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # validate that the algorithm image exists and retrieve the digest
        image, digest = self._get_image_digest(data["image"])
        if digest is None:
            return {
                "msg": "Image digest could not be determined"
            }, HTTPStatus.BAD_REQUEST

        # create the algorithm
        algorithm = db_Algorithm(
            name=data["name"],
            description=data.get("description", ""),
            image=image,
            partitioning=data["partitioning"],
            vantage6_version=data["vantage6_version"],
            code_url=data["code_url"],
            documentation_url=data.get("documentation_url", None),
            digest=digest,
            developer_id=g.user.id,
            submission_comments=data.get("submission_comments", None),
        )
        algorithm.save()

        # If reviews are disabled, approve the algorithm immediately
        approved = False
        if self.config.get("dev", {}).get("disable_review", False):
            algorithm.approve()
            approved = True

        # create the algorithm's subresources
        for function in data["functions"]:
            # create the function
            func = Function(
                name=function["name"],
                display_name=function.get("display_name", ""),
                description=function.get("description", ""),
                step_type=function["step_type"],
                standalone=function.get("standalone", True),
                algorithm_id=algorithm.id,
            )
            func.save()
            # create the arguments. Note that the field `conditional_on_id` is skipped
            # because it might not exist yet (depending on the order of the arguments)
            for argument in function.get("arguments", []):
                arg = Argument(
                    name=argument["name"],
                    display_name=argument.get("display_name", ""),
                    description=argument.get("description", ""),
                    type_=argument["type_"],
                    has_default_value=argument.get("has_default_value", False),
                    default_value=argument.get("default_value", None),
                    conditional_operator=argument.get("conditional_operator", None),
                    conditional_value=argument.get("conditional_value", None),
                    is_frontend_only=argument.get("is_frontend_only", False),
                    function_id=func.id,
                )
                arg.save()
            # after creating the arguments, all have had their IDs assigned so we can
            # now set the column `conditional_on_id`
            for argument in function.get("arguments", []):
                arg = Argument.get_by_name(argument["name"], func.id)
                if argument.get("conditional_on"):
                    conditional_on = Argument.get_by_name(
                        argument["conditional_on"], func.id
                    )
                    arg.conditional_on_id = conditional_on.id
                    arg.save()
                if argument.get("allowed_values", []):
                    for value in argument["allowed_values"]:
                        allowed_value = AllowedArgumentValue(
                            value=str(value), argument_id=arg.id
                        )
                        allowed_value.save()
            # create the databases
            for database in function.get("databases", []):
                db_ = Database(
                    name=database["name"],
                    description=database.get("description", ""),
                    function_id=func.id,
                    multiple=database.get(DATAFRAME_MULTIPLE_KEYWORD, False),
                )
                db_.save()
            # create the visualizations
            for visualization in function.get("ui_visualizations", []):
                vis = UIVisualization(
                    name=visualization["name"],
                    description=visualization.get("description", ""),
                    type_=visualization["type_"],
                    schema=visualization.get("schema", {}),
                    function_id=func.id,
                )
                vis.save()

        if not approved:
            # send email to users responsible to assign reviewers. Do this in a
            # separate thread to avoid blocking the response
            Thread(
                target=self._send_email_to_review_assigners,
                args=(
                    current_app._get_current_object(),
                    self.mail,
                    algorithm,
                    g.user.username,
                    self.config,
                    request.headers.get("store_url"),
                ),
            ).start()

        return algorithm_output_schema.dump(algorithm, many=False), HTTPStatus.CREATED

    @staticmethod
    def _send_email_to_review_assigners(
        app: Flask,
        mail: Mail,
        algorithm: db_Algorithm,
        submitting_user_name: str,
        config: dict,
        store_url: str | None,
    ) -> None:
        """
        When new algorithm is created, send email to users responsible to assign
        reviewers.

        Parameters
        ----------
        app : Flask
            Flask app instance
        mail: flask_mail.Mail
            Flask mail instance
        algorithm : Algorithm
            Algorithm that has been created
        submitting_user_name : str
            Username of the user that submitted the algorithm
        config : dict
            Configuration dictionary
        store_url : str | None
            URL of the algorithm store
        """
        smtp_settings = config.get("smtp", {})
        if not smtp_settings:
            log.warning(
                "No SMTP settings found. No emails will be sent to alert "
                "algorithm managers that reviews have to be assigned."
            )
            return
        email_sender = smtp_settings.get("email_from", DEFAULT_EMAIL_FROM_ADDRESS)
        support_email = config.get("support_email", DEFAULT_SUPPORT_EMAIL_ADDRESS)

        # get users with the role 'algorithm manager'
        log.info(
            "Sending email to alert store administrators that reviewers have to be "
            "assigned."
        )
        algorithm_managers = db.User.get_by_permission("review", Operation.CREATE)
        # TODO v5+ email is always present for all users, so remove this check
        algorithm_managers = [am for am in algorithm_managers if am.email]
        if not algorithm_managers:
            log.warning(
                "No users with known email addresses found that can assign "
                "reviewers. No email will be sent."
            )

        # send email to each algorithm manager
        for algo_manager in algorithm_managers:
            other_admins_msg = ""
            if len(algorithm_managers) > 1:
                other_admins_msg = (
                    f", together with {len(algorithm_managers) - 1} other user(s)"
                )
            template_vars = {
                "admin_username": algo_manager.username,
                "algorithm_name": algorithm.name,
                "store_url": get_server_url(config, store_url),
                "dev_username": submitting_user_name,
                "other_admins": other_admins_msg,
                "support_email": support_email,
            }
            with app.app_context():
                mail.send_email(
                    subject="New vantage6 algorithm needs reviewer assignment",
                    sender=email_sender,
                    recipients=[algo_manager.email],
                    text_body=render_template(
                        "mail/new_algorithm.txt", **template_vars
                    ),
                    html_body=render_template(
                        "mail/new_algorithm.html", **template_vars
                    ),
                )


class Algorithm(AlgorithmBaseResource):
    """Resource for /algorithm/<id>"""

    @with_permission_to_view_algorithms()
    def get(self, id):
        """Get algorithm
        ---
        description: Return an algorithm specified by ID.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: ID of the algorithm

        responses:
          200:
            description: OK
          401:
            description: Unauthorized
          404:
            description: Algorithm not found

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        algorithm = db_Algorithm.get(id)
        if not algorithm:
            return {"msg": "Algorithm not found"}, HTTPStatus.NOT_FOUND

        return algorithm_output_schema.dump(algorithm, many=False), HTTPStatus.OK

    @with_permission(module_name, Operation.DELETE)
    def delete(self, id):
        """Delete algorithm
        ---
        description: Delete an algorithm specified by ID.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: ID of the algorithm

        responses:
          200:
            description: OK
          401:
            description: Unauthorized
          404:
            description: Algorithm not found

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        algorithm = db_Algorithm.get(id)
        if not algorithm:
            return {"msg": "Algorithm not found"}, HTTPStatus.NOT_FOUND

        # delete all subresources and finally the algorithm itself
        for function in algorithm.functions:
            for database in function.databases:
                database.delete()
            for argument in function.arguments:
                for allowed_value in argument.allowed_values:
                    allowed_value.delete()
                argument.delete()
            for visualization in function.ui_visualizations:
                visualization.delete()
            function.delete()
        algorithm.delete()

        return {"msg": f"Algorithm id={id} was successfully deleted"}, HTTPStatus.OK

    @with_permission(module_name, Operation.EDIT)
    def patch(self, id):
        """Patch algorithm
        ---
        description: Modify an algorithm specified by ID.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Algorithm id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Name of the algorithm
                  description:
                    type: string
                    description: Description of the algorithm
                  image:
                    type: string
                    description: Docker image URL
                  partitioning:
                    type: string
                    description: Type of partitioning. Can be 'horizontal' or
                      'vertical'
                  vantage6_version:
                    type: string
                    description: Version of vantage6 that the algorithm is
                      built with / for
                  code_url:
                    type: string
                    description: URL to the algorithm code repository
                  documentation_url:
                    type: string
                    description: URL to the algorithm documentation
                  submission_comments:
                    type: string
                    description: Comments done by the developer to the submission
                  functions:
                    type: array
                    description: List of functions that are available in the algorithm.
                      If provided, all existing functions will be replaced by the new
                      ones.
                    items:
                      properties:
                        name:
                          type: string
                          description: Name of the function
                        display_name:
                          type: string
                          description: Name of the function
                        description:
                          type: string
                          description: Description of the function
                        step_type:
                          type: string
                          description: Step type of the function. Can be
                            'data_extraction', 'preprocessing', 'federated_compute',
                            'central_compute', or 'postprocessing'
                        standalone:
                          type: boolean
                          description: Whether this function produces useful results
                            when running it by itself
                        databases:
                          type: array
                          description: List of databases that this function
                            uses
                          items:
                            properties:
                              name:
                                type: string
                                description: Name of the database in the
                                  function
                              description:
                                type: string
                                description: Description of the database
                        arguments:
                          type: array
                          description: List of arguments that this function
                            uses
                          items:
                            properties:
                              name:
                                type: string
                                description: Name of the argument in the
                                  function
                              display_name:
                                type: string
                                description: Display name of the argument
                              description:
                                type: string
                                description: Description of the argument
                              type:
                                type: string
                                description: Type of argument. Can be 'string',
                                  'integer', 'float', 'boolean', 'json',
                                  'column', 'organizations' or 'organization'
                              has_default_value:
                                type: boolean
                                description: Whether the argument has a default
                                  value. If true, the 'default_value' field must be
                                  provided. Default is false.
                              default_value:
                                type: string | int | float | boolean | list | None
                                description: Default value of the argument. The type
                                  should match the 'type' field, e.g. if 'type' is
                                  'integer', 'default_value' should be an integer.
                                  To set an empty (null) default value, use None.
                              conditional_on:
                                type: string
                                description: Name of the argument that this argument
                                  is conditional on.
                              conditional_operator:
                                type: string
                                description: Comparator used for the conditional
                                  argument. Can be one of '==', '!=', '>', '<', '>=',
                                  '<='.
                              conditional_value:
                                type: string
                                description: Value that the argument should be compared
                                  to.
                              is_frontend_only:
                                type: boolean
                                description: Frontend-only arguments are displayed in
                                  the UI, but are not passed to the algorithm. Default
                                  is false.
                        ui_visualizations:
                          type: array
                          description: List of visualizations that are available in
                            the algorithm
                          items:
                            properties:
                              name:
                                type: string
                                description: Name of the visualization
                              description:
                                type: string
                                description: Description of the visualization
                              type:
                                type: string
                                description: Type of visualization.
                              schema:
                                type: object
                                description: Schema that describes the visualization.
                  refresh_digest:
                    type: boolean
                    description: If true, the digest of the image will be refreshed
                      and stored in the database. Note that this is also done whenever
                      the image is changed.

        responses:
          201:
            description: Algorithm created successfully
          400:
            description: Invalid input
          401:
            description: Unauthorized
          403:
            description: Forbidden action

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        algorithm = db_Algorithm.get(id)
        if not algorithm:
            return {"msg": "Algorithm not found"}, HTTPStatus.NOT_FOUND

        data = request.get_json(silent=True)

        # validate the request body
        try:
            data = algorithm_input_patch_schema.load(data, partial=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # algorithms can no longer be edited if they are in the review process or have
        # already been through it.
        if algorithm.approved_at is not None:
            return {
                "msg": "Approved algorithms cannot be edited. Please submit a new "
                "algorithm and go through the review process if you want to update it."
            }, HTTPStatus.FORBIDDEN
        elif algorithm.invalidated_at is not None:
            return {
                "msg": "Invalidated algorithms cannot be edited. Please submit a new "
                "algorithm and go through the review process if you want to update it."
            }, HTTPStatus.FORBIDDEN
        elif algorithm.reviews and any(
            [r.is_review_finished() for r in algorithm.reviews]
        ):
            return {
                "msg": "This algorithm has at least one submitted review, and can "
                "therefore no longer be edited. Please submit a new algorithm and go "
                "through the review process if you want to update this algorithm."
            }, HTTPStatus.FORBIDDEN

        fields = [
            "name",
            "display_name",
            "description",
            "partitioning",
            "vantage6_version",
            "code_url",
            "documentation_url",
            "submission_comments",
        ]
        for field in fields:
            if field in data and data.get(field) is not None:
                setattr(algorithm, field, data.get(field))

        image = data.get("image")
        # If image is updated or refresh_digest is set to True, update the digest of the
        # image.
        if image != algorithm.image or data.get("refresh_digest", False):
            image, digest = self._get_image_digest(image)
            if digest is None:
                return {
                    "msg": "Image digest could not be determined"
                }, HTTPStatus.BAD_REQUEST
            algorithm.image = image
            algorithm.digest = digest

        if (functions := data.get("functions")) is not None:
            for function in algorithm.functions:
                for argument in function.arguments:
                    for allowed_value in argument.allowed_values:
                        allowed_value.delete()
                    argument.delete()
                for db_ in function.databases:
                    db_.delete()
                for visualization in function.ui_visualizations:
                    visualization.delete()
                function.delete()

            for new_function in functions:
                func = Function(
                    name=new_function["name"],
                    description=new_function.get("description", ""),
                    display_name=new_function.get("display_name", ""),
                    step_type=new_function["step_type"],
                    standalone=new_function.get("standalone", True),
                    algorithm_id=id,
                )
                func.save()

                # create arguments. Note that the field `conditional_on_id` is skipped
                # because it might not exist yet (depending on the order of the
                # arguments)
                for argument in new_function.get("arguments", []):
                    arg = Argument(
                        name=argument["name"],
                        display_name=argument.get("display_name", ""),
                        description=argument.get("description", ""),
                        type_=argument["type_"],
                        has_default_value=argument.get("has_default_value", False),
                        default_value=argument.get("default_value", None),
                        conditional_operator=argument.get("conditional_operator", None),
                        conditional_value=argument.get("conditional_value", None),
                        is_frontend_only=argument.get("is_frontend_only", False),
                        function_id=func.id,
                    )
                    arg.save()
                # after creating the arguments, all have had their IDs assigned so we
                # can now set the column `conditional_on_id`
                for argument in new_function.get("arguments", []):
                    arg = Argument.get_by_name(argument["name"], func.id)
                    if argument.get("conditional_on"):
                        conditional_on = Argument.get_by_name(
                            argument["conditional_on"], func.id
                        )
                        arg.conditional_on_id = conditional_on.id
                        arg.save()
                    if argument.get("allowed_values", []):
                        for value in argument["allowed_values"]:
                            allowed_value = AllowedArgumentValue(
                                value=str(value), argument_id=arg.id
                            )
                            allowed_value.save()
                # Create databases and visualizations
                for database in new_function.get("databases", []):
                    db = Database(
                        name=database["name"],
                        description=database.get("description", ""),
                        function_id=func.id,
                        multiple=database.get(DATAFRAME_MULTIPLE_KEYWORD, False),
                    )
                    db.save()
                for visualization in new_function.get("ui_visualizations", []):
                    vis = UIVisualization(
                        name=visualization["name"],
                        description=visualization.get("description", ""),
                        type_=visualization["type"],
                        schema=visualization.get("schema", {}),
                        function_id=func.id,
                    )
                    vis.save()

        algorithm.save()

        return algorithm_output_schema.dump(algorithm, many=False), HTTPStatus.OK


class AlgorithmInvalidate(AlgorithmStoreResources):
    """Resource for /algorithm/<id>/invalidate"""

    @with_permission(module_name, Operation.DELETE)
    def post(self, id):
        """Invalidate algorithm

        ---
        description: >-
          Invalidate an algorithm specified by ID. This is an alternative to completely
          removing an algorithm from the store - the advantage of invalidating is that
          the algorithm metadata is still available. This endpoint should be used when
          an algorithm is removed from a project. If on the other hand a newer version
          of the algorithm is uploaded, the old version will be invalidated
          automatically.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: ID of the algorithm

        responses:
          200:
            description: OK
          401:
            description: Unauthorized
          404:
            description: Algorithm not found

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """

        algorithm: db.Algorithm = db_Algorithm.get(id)
        if not algorithm:
            return {"msg": "Algorithm not found"}, HTTPStatus.NOT_FOUND

        # invalidate the algorithm
        algorithm.invalidated_at = datetime.datetime.now(datetime.timezone.utc)
        algorithm.status = AlgorithmStatus.REMOVED.value
        algorithm.save()

        # Also invalidate any reviews that were still active
        for review in algorithm.reviews:
            if not review.is_review_finished():
                review.status = ReviewStatus.DROPPED.value
                review.save()

        return {"msg": f"Algorithm id={id} was successfully invalidated"}, HTTPStatus.OK
