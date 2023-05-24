from __future__ import annotations

import math
import logging
import flask
import sqlalchemy

from urllib.parse import urlencode

from vantage6.common import logger_name
from vantage6.server import db

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class Page:
    """
    Definition of a page of items return by the API.

    Parameters
    ----------
    items : list[db.Base]
        List of database resources on this page
    page : int
        Current page number
    page_size : int
        Number of items per page
    total : int
        Total number of items

    Attributes
    ----------
    current_page : int
        Current page number
    items : list[db.Base]
        List of resources on the current page
    previous_page : int
        Page number of the previous page
    next_page : int
        Page number of the next page
    has_previous : bool
        True if there is a previous page, False otherwise
    has_next : bool
        True if there is a next page, False otherwise
    total : int
        Total number of items
    pages : int
        Total number of pages
    """
    def __init__(self, items: list[db.Base], page: int, page_size: int,
                 total: int) -> None:
        self.current_page = page
        self.items = items
        self.previous_page = None
        self.next_page = None
        self.has_previous = page > 1
        if self.has_previous:
            self.previous_page = page - 1
        previous_items = (page - 1) * page_size
        self.has_next = previous_items + len(items) < total
        if self.has_next:
            self.next_page = page + 1
        self.total = total
        self.pages = int(math.ceil(total / float(page_size)))


class Pagination:
    """
    Class that handles pagination of a query.

    Parameters
    ----------
    items : list[db.Base]
        List of database resources to paginate
    page : int
        Current page number
    page_size : int
        Number of items per page
    total : int
        Total number of items
    request : flask.Request
        Request object

    Attributes
    ----------
    page : Page
        Page object
    request : flask.Request
        Request object
    """
    def __init__(self, items: list[db.Base], page: int, page_size: int,
                 total: int, request: flask.Request) -> None:
        self.page = Page(items, page, page_size, total)
        self.request = request

    @property
    def link_header(self) -> str:
        """
        Puts links to other pages in the response header.

        Returns
        -------
        str
            Link header
        """
        link_strs = [f'<{url}>; rel={rel}' for rel, url in
                     self.metadata_links.items()]
        return ','.join(link_strs)

    @property
    def headers(self) -> dict:
        """
        Set the headers for the response.

        Returns
        -------
        dict
            Response headers
        """
        return {
            'total-count': self.page.total,
            'Link': self.link_header
        }

    @property
    def metadata_links(self) -> dict:
        """
        Construct links to other pages.

        Returns
        -------
        dict
            Links to other pages
        """
        url = self.request.path
        args = self.request.args.copy()

        navs = [
            {'rel': 'first', 'page': 1},
            {'rel': 'previous', 'page': self.page.previous_page},
            {'rel': 'self', 'page': self.page.current_page},
            {'rel': 'next', 'page': self.page.next_page},
            {'rel': 'last', 'page': self.page.pages},
        ]

        links = {}
        for nav in navs:
            if nav['page']:
                args['page'] = nav['page']
                links[nav['rel']] = f'{url}?{urlencode(args)}'

        return links

    @classmethod
    def from_query(cls, query: sqlalchemy.orm.query,
                   request: flask.Request) -> Pagination:
        """
        Create a Pagination object from a query.

        Parameters
        ----------
        query : sqlalchemy.orm.query
            Query to paginate
        request : flask.Request
            Request object

        Returns
        -------
        Pagination
            Pagination object
        """
        # We remove the ordering of the query since it doesn't matter for
        # getting a count and might have performance implications as discussed
        # on this Flask-SqlAlchemy issue
        # https://github.com/mitsuhiko/flask-sqlalchemy/issues/100
        total = query.distinct().order_by(None).count()

        # check if pagination is desired, else return all records
        page_id = request.args.get('page')
        if not page_id:
            page_id = 1
            per_page = total or 1
        else:
            page_id = int(page_id)
            per_page = int(request.args.get('per_page', 10))

        if page_id <= 0:
            raise AttributeError('page needs to be >= 1')
        if per_page <= 0:
            raise AttributeError('per_page needs to be >= 1')

        items = query.distinct().limit(per_page).offset((page_id-1)*per_page)\
            .all()

        return cls(items, page_id, per_page, total, request)

    @classmethod
    def from_list(cls, items: list[db.Base],
                  request: flask.Request) -> Pagination:
        """
        Create a Pagination object from a list of database objects.

        Parameters
        ----------
        items : list[db.Base]
            List of database objects to paginate
        request : flask.Request
            Request object

        Returns
        -------
        Pagination
            Pagination object
        """
        page_id = request.args.get('page')
        total = len(items)
        if not page_id:
            page_id = 1
            per_page = total or 1
        else:
            page_id = int(page_id)
            per_page = int(request.args.get('per_page', 10))

        if page_id <= 0:
            raise AttributeError('page needs to be >= 1')
        if per_page <= 0:
            raise AttributeError('per_page needs to be >= 1')

        beginning = (page_id - 1) * per_page
        ending = page_id * per_page
        if ending > total:
            ending = total
        items = items[beginning:ending]

        return cls(items, page_id, per_page, total, request)
