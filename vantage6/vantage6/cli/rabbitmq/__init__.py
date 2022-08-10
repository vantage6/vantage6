"""RabbitMQ utilities."""
from typing import Dict

from vantage6.common import is_ip_address


def split_rabbitmq_uri(rabbit_uri: str) -> Dict:
    """Get details (user, pass, host, vhost, port) from a RabbitMQ uri.

    Parameters
    ----------
    rabbit_uri: str
        URI of RabbitMQ service ('amqp://$user:$pass@$host:$port/$vhost')

    Returns
    -------
    Dict[str]
        The vhost defined in the RabbitMQ URI
    """
    (user_details, location_details) = rabbit_uri.split('@', 1)
    (user, password) = user_details.split('/')[-1].split(':', 1)
    (host, remainder) = location_details.split(':', 1)
    port, vhost = remainder.split('/', 1)
    return {
        'user': user,
        'password': password,
        'host': host,
        'port': port,
        'vhost': vhost,
    }


def is_local_address(rabbit_uri: str) -> bool:
    """
    Test if the host of a RabbitMQ uri is an external IP address or not

    Parameters
    ----------
    rabbit_uri: str
        The connection URI to the RabbitMQ service from the configuration

    Returns
    -------
    bool:
        Whether or not the rabbit_uri points to a service to be set up locally
    """
    uri_info = split_rabbitmq_uri(rabbit_uri=rabbit_uri)
    return not is_ip_address(uri_info['host'])
