# -*- coding: utf-8 -*-
import logging

from flask import request, g
from flask_restful import Api
from http import HTTPStatus
from sqlalchemy import or_

from vantage6.server import db
from vantage6.server.resource.common.pagination import Pagination
from vantage6.server.resource.common.input_schema import (
    AlgorithmStoreInputSchema
)
from vantage6.server.permission import RuleCollection, Operation as P
from vantage6.server.resource.common.output_schema import AlgorithmStoreSchema
from vantage6.server.resource import (
    with_user,
    ServicesResources
)


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the collaboration resource.

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
        AlgorithmStores,
        api_base + '/algorithmstore',
        endpoint='algorithm_store_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    api.add_resource(
        AlgorithmStore,
        api_base + '/algorithmstore/<int:id>',
        endpoint='algorithm_store_with_id',
        methods=('GET', 'PATCH', 'DELETE'),
        resource_class_kwargs=services
    )


algorithm_store_schema = AlgorithmStoreSchema()
algorithm_store_input_schema = AlgorithmStoreInputSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class AlgorithmStoreBase(ServicesResources):
    """ Base class for algorithm store resources. """

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r_col: RuleCollection = getattr(self.permissions, "collaboration")


class AlgorithmStores(AlgorithmStoreBase):
    """ Resource for /algorithm """

    @with_user
    def get(self):
        """Returns a list of available algorithm stores
        ---
        description: >-
          Returns a list of available algorithm stores. Depending on your
          permission, all algorithm stores are shown or only algorithm stores
          in which your organization participates.\n\n

          ### Permission Table\n
          |Rulename|Scope|Operation|Assigned to Node|Assigned to Container|
          Description|\n
          | -- | -- | -- | -- | -- | -- |\n
          |Collaboration|Global|View|❌|❌|All algorithm stores|\n
          |Collaboration|Organization|View|❌|❌|Algorithm stores within
          collaborations in which your organization participates|\n\n

          Accessible to users.

        parameters:
          - in: query
            name: name
            schema:
              type: string
            description: >-
              Name to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: url
            schema:
              type: string
            description: >-
              Algorithm store URL to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: collaboration_id
            schema:
              type: integer
            description: Collaboration id
          - in: query
            name: page
            schema:
              type: integer
            description: Page number for pagination (default=1)
          - in: query
            name: per_page
            schema:
              type: integer
            description: Number of items per page (default=10)
          - in: query
            name: sort
            schema:
              type: string
            description: >-
              Sort by one or more fields, separated by a comma. Use a minus
              sign (-) in front of the field to sort in descending order.

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          400:
            description: Improper values for pagination or sorting parameters
          404:
            description: Collaboration with specified id is not found

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        # TODO make an option to GET algorithm stores that are available to all
        # collaborations

        # obtain organization from authenticated
        auth_org = self.obtain_auth_organization()
        q = g.session.query(db.AlgorithmStore)
        args = request.args

        # filter by a field of this endpoint
        for param in ['name', 'url']:
            if param in args:
                q = q.filter(
                    getattr(db.AlgorithmStore, param).like(args[param])
                )

        if 'collaboration_id' in args:
            collab = db.Collaboration.get(args['collaboration_id'])
            if not collab:
                return {'msg': 'Collaboration not found'}, \
                    HTTPStatus.NOT_FOUND
            # TODO generalize this check (make it available as part of the
            # permission class)
            if not self.r_col.v_glo.can():
                orgs_in_collab = [org.id for org in collab.organizations]
                if not (self.r_col.v_org.can() and
                        auth_org.id in orgs_in_collab):
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED
            q = q.filter(or_(
                db.AlgorithmStore.collaboration_id == args['collaboration_id'],
                db.AlgorithmStore.collaboration_id.is_(None)
            ))

        # filter based on permissions
        if not self.r_col.v_glo.can():
            collab_ids = [c.id for c in auth_org.collaborations]
            if self.r_col.v_org.can():
                q = q.filter(
                    db.AlgorithmStore.collaboration_id.in_(collab_ids)
                )
            else:
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # paginate the results
        try:
            page = Pagination.from_query(q, request, db.AlgorithmStore)
        except (ValueError, AttributeError) as e:
            return {'msg': str(e)}, HTTPStatus.BAD_REQUEST

        # serialize models
        return self.response(page, algorithm_store_schema)

    @with_user
    def post(self):
        """ Add algorithm store to a collaboration
        ---
        description: >-
          Register an algorithm store to a collaboration. Its algorithms will
          be available for that collaboration from then on.\n\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to Node|Assigned to
          Container|Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Add algorithm store to a
          collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Add algorithm store to a
          collaboration that your organization is a member of|\n\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable name for the algorithm store
                  url:
                    type: string
                    description: URL to the algorithm store
                  collaboration_id:
                    type: integer
                    description: Collaboration id to which the algorithm store
                      will be added. If not given, the algorithm store will be
                      available to all collaborations.

        responses:
          200:
            description: Ok
          400:
            description: Wrong input data or algorithm store is already
              available for the collaboration
          401:
            description: Unauthorized
          404:
            description: Collaboration with specified id is not found

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        data = request.get_json()
        # validate request body
        errors = algorithm_store_input_schema.validate(data)
        if errors:
            return {'msg': 'Request body is incorrect', 'errors': errors}, \
                HTTPStatus.BAD_REQUEST

        # check if collaboration exists
        collaboration_id = data.get('collaboration_id', None)
        if collaboration_id:
            collaboration = db.Collaboration.get(collaboration_id)
            if not collaboration:
                return {'msg': 'Collaboration not found'}, \
                    HTTPStatus.NOT_FOUND

        # check permissions
        if not collaboration_id and not self.r_col.e_glo.can():
            return {'msg': 'You lack the permission to add algorithm stores '
                    'for all collaborations!'}, \
                HTTPStatus.UNAUTHORIZED
        elif not self.r_col.can_for_col(P.EDIT, collaboration_id):
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        # check if algorithm store is already available for the collaboration
        existing_algorithm_stores = db.AlgorithmStore.get_by_url(data['url'])
        if existing_algorithm_stores:
            collabs_with_algo_store = [a.id for a in existing_algorithm_stores]
            if None in collabs_with_algo_store:
                return {'msg': 'Algorithm store is already available for all '
                        'collaborations'}, \
                    HTTPStatus.BAD_REQUEST
            if collaboration_id in collabs_with_algo_store:
                return {'msg': 'Algorithm store is already available for this '
                        'collaboration'}, \
                    HTTPStatus.BAD_REQUEST
            if not collaboration_id:
                # algorithm store is currently available for some
                # collaborations, but now it will be available for all of them.
                # Remove the records that only make it available to some
                # collaborations (this prevents duplicates)
                for algo_store in existing_algorithm_stores:
                    algo_store.delete()

        algorithm_store = db.AlgorithmStore(
            name=data['name'],
            url=data['url'],
            collaboration_id=collaboration_id
        )
        algorithm_store.save()

        return algorithm_store_schema.dump(algorithm_store), HTTPStatus.CREATED


class AlgorithmStore(AlgorithmStoreBase):
    """ Resource for /algorithm/<id> """

    @with_user
    def get(self, id):
        """ Get algorithm store record
        ---
        description: >-
          Returns a specific algorithm store record.\n

          ### Permission Table\n
          |Rulename|Scope|Operation|Assigned to Node|Assigned to Container|
          Description|\n
          | -- | -- | -- | -- | -- | -- |\n
          |Collaboration|Global|View|❌|❌|All algorithm stores|\n
          |Collaboration|Organization|View|❌|❌|Algorithm stores of
          collaborations in which your organization participates|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Collaboration id
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Algorithm store with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        algorithm_store = db.AlgorithmStore.get(id)

        # check that collaboration exists, unlikely to happen without ID
        if not algorithm_store:
            return {"msg": f"Algorithm store id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        # verify that the user organization is within the collaboration
        # algorithm stores that are available to all collaborations are
        # always visible
        if not self.r_col.v_glo.can():
            auth_org_id = self.obtain_organization_id()
            ids = [
                org.id for org in algorithm_store.collaboration.organizations
            ]
            if not (
                self.r_col.v_org.can() and
                (auth_org_id in ids or not algorithm_store.collaboration_id)
            ):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return algorithm_store_schema.dump(algorithm_store, many=False), \
            HTTPStatus.OK  # 200

    @with_user
    def patch(self, id):
        """ Update algorithm store record
        ---
        description: >-
          Updates the linked algorithm store with the specified id.\n\n
          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Update any algorithm store|\n
          |Collaboration|Collaboration|Edit|❌|❌|Update algorithm stores
          within a collaboration that your organization is a member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Algorithm store id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable label
                  url:
                    type: string
                    description: URL to the algorithm store
                  collaboration_id:
                    type: integer
                    description: Collaboration id to which the algorithm store
                      will be added. If set to None, the algorithm store will
                      be available to all collaborations.

        responses:
          200:
            description: Ok
          404:
            description: Algorithm store with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        algorithm_store = db.AlgorithmStore.get(id)
        # check if collaboration exists
        if not algorithm_store:
            return {"msg": f"Algorithm store with id={id} can not be found"}, \
                HTTPStatus.NOT_FOUND  # 404

        # validate request body
        data = request.get_json()
        errors = algorithm_store_input_schema.validate(data, partial=True)
        if errors:
            return {'msg': 'Request body is incorrect', 'errors': errors}, \
                HTTPStatus.BAD_REQUEST

        # verify permissions - check permission for old collaboration
        collaboration_id_old = algorithm_store.collaboration_id
        if not self.r_col.can_for_col(P.EDIT, collaboration_id_old):
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        # verify permissions - check permission for new collaboration (if
        # specified)
        data = request.get_json()
        if "collaboration_id" in data:
            collaboration_id_new = data["collaboration_id"]
            if not self.r_col.can_for_col(P.EDIT, collaboration_id_new):
                return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED

        # only update fields that are provided
        fields = ["name", "url"]
        for field in fields:
            if field in data and data[field] is not None:
                setattr(algorithm_store, field, data[field])
        # update collaboration_id if specified - also if it is set to None (
        # that makes it available to all collaborations)
        if "collaboration_id" in data:
            algorithm_store.collaboration_id = data["collaboration_id"]

        algorithm_store.save()

        return algorithm_store_schema.dump(algorithm_store, many=False), \
            HTTPStatus.OK  # 200

    @with_user
    def delete(self, id):
        """ Delete linked algorithm store record
        ---
        description: >-
          Removes the algorithm store from the database entirely.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Remove any algorithm store from any
          collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Remove any algorithm store
          from a collaboration that your organization is a member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Algorithm store id
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Algorithm store with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """

        algorithm_store = db.AlgorithmStore.get(id)
        if not algorithm_store:
            return {"msg": f"Algorithm store id={id} is not found"}, \
                HTTPStatus.NOT_FOUND

        # verify permissions
        if not self.r_col.can_for_col(
            P.EDIT, algorithm_store.collaboration_id
        ):
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        algorithm_store.delete()
        return {"msg": f"Algorithm store id={id} successfully deleted"}, \
            HTTPStatus.OK
