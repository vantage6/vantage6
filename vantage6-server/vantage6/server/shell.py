import sys

from sqlalchemy.engine.url import make_url

from vantage6.server import db, util
from vantage6.server.configuration.configuration_wizard import (
    get_config_location
)


def init(environment):

    ctx = util.AppContext(
        "server",
        instance_name='default'
    )

    cfg_filename = get_config_location(ctx, None, force_create=False)

    print('-' * 80)
    print(f'using environment: {environment}')
    print(f'cfg_filename: {cfg_filename}')
    print('-' * 80)

    ctx.init(cfg_filename, environment, setup_logging=False)

    # initialize database from environment
    uri = ctx.get_database_location()
    url = make_url(uri)

    print()
    print("Initializing the database")
    print("  driver:   {}".format(url.drivername))
    print("  host:     {}".format(url.host))
    print("  port:     {}".format(url.port))
    print("  database: {}".format(url.database))
    print("  username: {}".format(url.username))

    db.init(uri)


if __name__ == "__main__":
    environment = sys.argv[1]
    init(environment)
