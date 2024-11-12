from http import HTTPStatus
from flask import request
from flask_mail import Mail
from flask_restful import Resource, Api

from vantage6.backend.common.permission import PermissionManagerBase
from vantage6.backend.common.resource.output_schema import BaseHATEOASModelSchema
from vantage6.backend.common.resource.pagination import Page


class BaseServicesResources(Resource):
    """
    Flask resource base class

    Attributes
    ----------
    api : Api
        Api instance
    config: dict
        Configuration dictionary
    permissions : PermissionManagerBase
        Instance of class that manages permissions
    mail : Mail
        Flask Mail instance
    """

    def __init__(
        self, api: Api, config: dict, permissions: PermissionManagerBase, mail: Mail
    ):
        self.api = api
        self.config = config
        self.permissions = permissions
        self.mail = mail

    @staticmethod
    def is_included(field) -> bool:
        """
        Check that a `field` is included in the request argument context.

        Parameters
        ----------
        field : str
            Name of the field to check

        Returns
        -------
        bool
            True if the field is included, False otherwise
        """
        # The logic below intends to find 'x' both in 'include=y&include=x' and
        # 'include=x,y'.
        return field in [
            val for item in request.args.getlist("include") for val in item.split(",")
        ]

    def dump(self, page: Page, schema: BaseHATEOASModelSchema) -> dict:
        """
        Dump based on the request context (to paginate or not)

        Parameters
        ----------
        page : Page
            Page object to dump
        schema : BaseHATEOASModelSchema
            Schema to use for dumping

        Returns
        -------
        dict
            Dumped page
        """
        return schema.meta_dump(page)

    def response(self, page: Page, schema: BaseHATEOASModelSchema):
        """
        Prepare a valid HTTP OK response from a page object

        Parameters
        ----------
        page : Page
            Page object to dump
        schema : BaseHATEOASModelSchema
            Schema to use for dumping

        Returns
        -------
        tuple
            Tuple of (dumped page, HTTPStatus.OK, headers of the page)
        """
        return self.dump(page, schema), HTTPStatus.OK, page.headers
