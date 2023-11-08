# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/version'
"""
import logging

from flask import request
from flask_restful import Api
from http import HTTPStatus
from vantage6.common import logger_name
from vantage6.algorithm.store._version import __version__
from vantage6.algorithm.store.resource.schema.input_schema import (
    AlgorithmInputSchema
)
from vantage6.algorithm.store.resource.schema.output_schema import (
    AlgorithmOutputSchema
)
from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.argument import Argument
from vantage6.algorithm.store.model.database import Database
from vantage6.algorithm.store.model.function import Function
# TODO move to common / refactor
from vantage6.server.resource import AlgorithmStoreResources



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
        endpoint='algorithm_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )


algorithm_input_schema = AlgorithmInputSchema()
algorithm_output_schema = AlgorithmOutputSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Algorithms(AlgorithmStoreResources):
    """ Algorithm resource """

    def get(self):
        return {"version": __version__}, HTTPStatus.OK

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
                  functions:
                    type: array
                    description: List of functions that are available in the
                      algorithm
                    items:
                      properties:
                        name:
                          type: string
                          description: Name of the function
                        description:
                          type: string
                          description: Description of the function
                        type:
                          type: string
                          description: Type of function. Can be 'central' or
                            'federated'
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
                              description:
                                type: string
                                description: Description of the argument
                              type:
                                type: string
                                description: Type of argument. Can be 'string',
                                  'integer', 'float', 'boolean', 'json',
                                  'column', 'organizations' or 'organization'

        responses:
          201:
            description: Algorithm created successfully
          400:
            description: Invalid input

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        data = request.get_json()

        # validate the request body
        errors = algorithm_input_schema.validate(data)
        if errors:
            return {'msg': "Request body is incorrect", 'errors': errors}, \
                HTTPStatus.BAD_REQUEST

        # create the algorithm
        algorithm = Algorithm(
            name=data['name'],
            description=data.get('description', ''),
            image=data['image'],
            partitioning=data['partitioning'],
            vantage6_version=data['vantage6_version']
        )
        algorithm.save()

        # create the algorithm's subresources
        for function in data['functions']:
            # create the function
            func = Function(
                name=function['name'],
                description=function.get('description', ''),
                type=function['type'],
                algorithm_id=algorithm.id
            )
            func.save()
            # create the arguments
            arguments = function.get('arguments')
            if arguments:
                for argument in arguments:
                    arg = Argument(
                        name=argument['name'],
                        description=argument.get('description', ''),
                        type=argument['type'],
                        function_id=func.id
                    )
                    arg.save()
            # create the databases
            databases = function.get('databases')
            if databases:
                for database in databases:
                    db = Database(
                        name=database['name'],
                        description=database.get('description', ''),
                        function_id=func.id
                    )
                    db.save()

        return algorithm_output_schema.dump(algorithm, many=False), \
            HTTPStatus.CREATED
