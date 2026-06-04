"""
One-shot database initialization for HQ

This script can be run before uWSGI starts to ensure that:
- default roles exist and are up to date
- the root organization and root user exist

By doing this in a separate script, we can avoid that multiple processes try to
create the same database objects concurrently.

It reuses the same context and database setup as `run_hq`.
"""

import os
import sys

from vantage6.cli.context.hq import HQContext

from vantage6.hq import Database, HQApp


def main() -> None:
    if len(sys.argv) >= 2:
        config_file = sys.argv[1]
    else:
        config_file = os.environ.get("VANTAGE6_HQ_CONFIG_LOCATION", "/mnt/config.yaml")

    ctx = HQContext.from_external_config_file(
        config_file, system_folders=False, in_container=True
    )
    Database().connect(uri=ctx.get_database_uri(), allow_drop_all=False)

    app = HQApp(ctx)
    app.ensure_db_initialized()
    print("HQ database initialized")


if __name__ == "__main__":
    main()
