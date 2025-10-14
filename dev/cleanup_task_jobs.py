"""
Cleanup jobs in the task namespace.
"""

import argparse

from vantage6.cli.node.stop import cleanup_task_jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup Vantage6 task jobs")
    parser.add_argument("--namespace", type=str, help="Task namespace")
    args = parser.parse_args()

    namespace = args.namespace
    success = cleanup_task_jobs(namespace, all_nodes=True)
    return 0 if success else 1


if __name__ == "__main__":
    main()
