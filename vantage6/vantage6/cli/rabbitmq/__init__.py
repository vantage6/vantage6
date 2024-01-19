"""RabbitMQ utilities."""


def split_rabbitmq_uri(rabbit_uri: str) -> dict:
    """
    Get details (user, pass, host, vhost, port) from a RabbitMQ uri.

    Parameters
    ----------
    rabbit_uri: str
        URI of RabbitMQ service ('amqp://$user:$pass@$host:$port/$vhost')

    Returns
    -------
    dict[str]
        The vhost defined in the RabbitMQ URI
    """
    (user_details, location_details) = rabbit_uri.split("@", 1)
    (user, password) = user_details.split("/")[-1].split(":", 1)
    (host, remainder) = location_details.split(":", 1)
    port, vhost = remainder.split("/", 1)
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "vhost": vhost,
    }
