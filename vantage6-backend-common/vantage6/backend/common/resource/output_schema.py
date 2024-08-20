import logging
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from flask import url_for
from sqlalchemy.ext.declarative import DeclarativeMeta

from vantage6.common import logger_name
from vantage6.backend.common.resource.pagination import Pagination


log = logging.getLogger(logger_name(__name__))


def create_one_to_many_link(obj: DeclarativeMeta, link_to: str, link_from: str) -> str:
    """
    Create an API link to get objects related to a given object.

    Parameters
    ----------
    obj : DeclarativeMeta
        Object to which the link is created
    link_to : str
        Name of the resource to which the link is created
    link_from : str
        Name of the resource from which the link is created

    Returns
    -------
    str
        API link

    Examples
    --------
    >>> create_one_to_many_link(obj, "node", "organization_id")
    "/api/node?organization_id=<obj.id>"
    """
    endpoint = link_to + "_without_id"
    values = {link_from: obj.id}
    return url_for(endpoint, **values)


class BaseHATEOASModelSchema(SQLAlchemyAutoSchema):
    """Base class for generating HATEOAS links for SQLAlchemy resources."""

    api = None

    def create_hateoas(
        self, name: str, obj: DeclarativeMeta, endpoint: str = None
    ) -> dict | None:
        """
        Create a HATEOAS link to a related object.

        Parameters
        ----------
        name : str
            Name of the related resource
        obj : Derivative of DeclarativeMeta class
            SQLAlchemy resource to which the link is created
        endpoint : str, optional
            Name of the endpoint to which the link is created, by default None.
            If None, the endpoint is assumed to be the same as the name of the
            related resource.

        Returns
        -------
        dict | None
            HATEOAS link to the related object, or None if the related object
            does not exist.
        """
        # get the related object
        elem = getattr(obj, name)

        # create the link
        endpoint = endpoint if endpoint else name
        if elem:
            return self._hateoas_link_from_related_resource(elem, endpoint)
        else:
            return None

    def _hateoas_link_from_related_resource(
        self, elem: DeclarativeMeta, name: str
    ) -> dict:
        """
        Construct a HATEOAS link from a related object.

        Parameters
        ----------
        obj : Derivative of DeclarativeMeta class
            SQLAlchemy resource for which the link is created
        name : str
            Name of the resource

        Returns
        -------
        dict
            HATEOAS link to the related object
        """
        _id = elem.id
        endpoint = name + "_with_id"
        if self.api:
            if not self.api.owns_endpoint(endpoint):
                Exception(f"Make sure {endpoint} exists!")

            verbs = list(self.api.app.url_map._rules_by_endpoint[endpoint][0].methods)
            verbs.remove("HEAD")
            verbs.remove("OPTIONS")
            url = url_for(endpoint, id=_id)
            return {"id": _id, "link": url, "methods": verbs}
        else:
            log.error("No API found?")

    def meta_dump(self, pagination: Pagination) -> dict:
        """
        Dump paginated database resources to a dictionary that has links
        to additional pages.

        Parameters
        ----------
        pagination : Pagination
            Paginated database resources

        Returns
        -------
        dict
            Dictionary with paginated database resources and links to
            additional pages.
        """
        data = self.dump(pagination.page.items, many=True)
        return {"data": data, "links": pagination.metadata_links}
