import math
import logging

from urllib.parse import urlencode
import sqlalchemy

from vantage6.common import logger_name
from vantage6.server.globals import DEFAULT_PAGE, DEFAULT_PAGE_SIZE

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class Page:

    def __init__(self, items, page, page_size, total):
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

    def __init__(self, items, page: int, page_size, total, request):
        self.page = Page(items, page, page_size, total)
        self.request = request

    @property
    def link_header(self) -> str:
        link_strs = [f'<{url}>; rel={rel}' for rel, url in
                     self.metadata_links.items()]
        return ','.join(link_strs)

    @property
    def headers(self):
        return {
            'total-count': self.page.total,
            'Link': self.link_header
        }

    @property
    def metadata_links(self) -> dict:
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
    def from_query(cls, query: sqlalchemy.orm.query, request):
        # Get the total number of records. We remove the ordering of the query
        # since it doesn't matter for getting a count and might have
        # performance implications as discussed on this Flask-SqlAlchemy issue:
        # https://github.com/mitsuhiko/flask-sqlalchemy/issues/100
        total = query.distinct().order_by(None).count()

        # Get the page and page size from the request
        try:
            page_id = int(request.args.get('page', DEFAULT_PAGE))
        except ValueError:
            raise ValueError("The 'page' parameter should be an integer")
        try:
            per_page = int(request.args.get('per_page', DEFAULT_PAGE_SIZE))
        except ValueError:
            raise ValueError("The 'per_page' parameter should be an integer")

        # Check if the page and page size are valid
        if page_id <= 0:
            raise ValueError("The 'page' parameter should be >= 1")
        elif per_page <= 0:
            raise ValueError("The 'per_page' parameter should be >= 1")
        elif total < (page_id-1) * per_page:
            raise ValueError(
                "The 'page' and/or 'per_page' parameter values are too large: "
                "there are no records present on this page"
            )

        # FIXME BvB 2020-02-09 good error handling if sort is not a valid
        #  field
        if request.args.get('sort', False):
            query = cls._add_sorting(query, request.args.get('sort'))

        items = query.distinct()\
            .limit(per_page)\
            .offset((page_id-1)*per_page)\
            .all()

        return cls(items, page_id, per_page, total, request)

    @staticmethod
    def _add_sorting(query: sqlalchemy.orm.query, sort_string: str
                     ) -> sqlalchemy.orm.query:
        """
        Add sorting to a query.

        Parameters
        ----------
        query : sqlalchemy.orm.query
            The query to add sorting to.
        sort : str
            The sorting to add. This can be a comma separated list of fields to
            sort on. The fields can be prefixed with a '-' to indicate a
            descending sort.
        """
        sort_list = sort_string.split(',')
        for sorter in sort_list:
            sorter = sorter.strip()
            if sorter.startswith('-'):
                query = query.order_by(sqlalchemy.desc(sorter[1:]))
            else:
                if sorter.startswith('+'):
                    sorter = sorter[1:]
                query = query.order_by(sorter)
        return query

    # TODO in v4+, remove this method if also removing the double endpoints
    @classmethod
    def from_list(cls, items: list, request):
        page_id = int(request.args.get('page', DEFAULT_PAGE))
        per_page = int(request.args.get('per_page', DEFAULT_PAGE_SIZE))
        total = len(items)

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
