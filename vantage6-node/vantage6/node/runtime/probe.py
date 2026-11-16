from vantage6.node.globals import ISOLATION_PROBE_CURL_MAX_TIME_SECONDS


def probe_args(url: str) -> list[str]:
    """curl arguments that exit with 0 only if ``url`` is reachable."""
    return [
        "-s",
        "-o",
        "/dev/null",
        "--max-time",
        str(ISOLATION_PROBE_CURL_MAX_TIME_SECONDS),
        url,
    ]
