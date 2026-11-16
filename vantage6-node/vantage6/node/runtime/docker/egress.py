import ipaddress
import re
from dataclasses import dataclass

from vantage6.common.enum import AlgorithmStepType

SQUID_PORT = 3128
DEFAULT_PORTS = (80, 443)

# Domains end up in the Squid configuration, so only allow what a domain can contain
_DOMAIN = re.compile(r"^\.?[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*$")


@dataclass(frozen=True)
class HttpWhitelist:
    domains: tuple[str, ...] = ()
    ips: tuple[str, ...] = ()
    ports: tuple[int, ...] = DEFAULT_PORTS


def parse_whitelist(config: dict | None) -> dict[AlgorithmStepType, HttpWhitelist]:
    """
    Read the HTTP(S) whitelist of a Docker node.

    Expected format, per algorithm step::

        whitelist:
          data_extraction:
            http:
              domains: [".example.org"]
              ips: ["10.0.0.0/8"]
              ports: [443]
    """
    whitelists = {}
    for step_name, rules in (config or {}).items():
        try:
            step = AlgorithmStepType(step_name)
        except ValueError as exc:
            raise ValueError(
                f"Unknown algorithm step '{step_name}' in the whitelist. Valid steps "
                f"are: {', '.join(AlgorithmStepType.list())}."
            ) from exc
        rules = rules or {}
        if "egress" in rules:
            raise ValueError(
                f"The whitelist of '{step_name}' uses Kubernetes NetworkPolicy rules "
                "('egress'), which do not apply to a Docker node. Use 'http' with "
                "'domains', 'ips' and 'ports' instead."
            )
        unknown = set(rules) - {"http"}
        if unknown:
            raise ValueError(
                f"Unknown whitelist settings for '{step_name}': {', '.join(unknown)}"
            )
        http = rules.get("http") or {}
        whitelist = HttpWhitelist(
            domains=tuple(_domain(d) for d in http.get("domains") or []),
            ips=tuple(
                str(ipaddress.ip_network(ip, strict=False))
                for ip in http.get("ips") or []
            ),
            ports=tuple(_port(p) for p in http.get("ports") or DEFAULT_PORTS),
        )
        if whitelist.domains or whitelist.ips:
            whitelists[step] = whitelist
    return whitelists


def _domain(domain: str) -> str:
    if not isinstance(domain, str) or not _DOMAIN.match(domain):
        raise ValueError(f"Invalid domain in whitelist: {domain!r}")
    return domain.lower()


def _port(port) -> int:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 < port < 65536:
        raise ValueError(f"Invalid port in whitelist: {port!r}")
    return port


def squid_config(whitelist: HttpWhitelist) -> str:
    lines = [f"acl allowed_ports port {' '.join(map(str, whitelist.ports))}"]
    if whitelist.domains:
        lines.append(f"acl whitelist_domain dstdomain {' '.join(whitelist.domains)}")
    if whitelist.ips:
        lines.append(f"acl whitelist_ip dst {' '.join(whitelist.ips)}")
    lines += [
        "http_access deny !allowed_ports",
        "http_access deny CONNECT !allowed_ports",
    ]
    if whitelist.domains:
        lines.append("http_access allow whitelist_domain")
    if whitelist.ips:
        lines.append("http_access allow whitelist_ip")
    lines += [
        "http_access deny all",
        f"http_port {SQUID_PORT}",
        "cache deny all",
        "pid_filename none",
        "access_log stdio:/dev/stdout",
        "cache_log stdio:/dev/stderr",
        "",
    ]
    return "\n".join(lines)
