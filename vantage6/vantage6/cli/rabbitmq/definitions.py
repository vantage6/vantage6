RABBITMQ_DEFINITIONS = {
    "rabbit_version": "3.6.6",
    "users": [
        {
            "name": "{{username}}",
            "password_hash": "{{password}}",
            "hashing_algorithm": "rabbit_password_hashing_sha256",
            "tags": "administrator",
        }
    ],
    "vhosts": [{"name": "{{vhost_name}}"}],
    "permissions": [
        {
            "user": "{{username}}",
            "vhost": "{{vhost_name}}",
            "configure": ".*",
            "write": ".*",
            "read": ".*",
        }
    ],
    "parameters": [],
    "policies": [],
    "queues": [],
    "exchanges": [],
    "bindings": [],
}
