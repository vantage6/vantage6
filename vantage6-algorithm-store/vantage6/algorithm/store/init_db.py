"""
One-shot database initialization for the algorithm store.

This script can be run before uWSGI starts to ensure that:
- default roles exist and are up to date
- the configured root user exists

By doing this in a separate script, we can avoid that multiple processes try to
create the same database objects concurrently.

It reuses the same context and database setup as run_store.
"""

import os
import sys

from vantage6.cli.context.algorithm_store import AlgorithmStoreContext

from vantage6.algorithm.store import (
    AlgorithmStoreApp,
    Database,
)


def main() -> None:
    if len(sys.argv) >= 2:
        config_file = sys.argv[1]
    else:
        config_file = os.environ.get(
            "VANTAGE6_STORE_CONFIG_LOCATION", "/mnt/config.yaml"
        )

    ctx = AlgorithmStoreContext.from_external_config_file(
        config_file, system_folders=False, in_container=True
    )
    Database().connect(uri=ctx.get_database_uri(), allow_drop_all=False)

    app = AlgorithmStoreApp(ctx)
    app.ensure_db_initialized()


if __name__ == "__main__":
    main()
