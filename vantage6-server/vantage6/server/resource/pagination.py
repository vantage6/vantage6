import math
import logging

from urllib.parse import urlencode
import sqlalchemy

from vantage6.common import logger_name

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
    def from_list(cls, items: list, request):
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
