RABBITMQ_DEFINITIONS = {
  "rabbit_version": "3.6.6",
  "users": [
   {
    "name": "{{username}}",
    "password_hash": "{{password}}",
    "hashing_algorithm": "rabbit_password_hashing_sha256",
    "tags": "administrator"  # TODO remove this tag?!
   }
  ],
  "vhosts": [
   {
    "name": "/test"  # TODO rename (in queue_manager.py)
   }
  ],
  "permissions": [
   {
    "user": "{{username}}",
    "vhost": "/test",
    "configure": ".*",
    "write": ".*",
    "read": ".*"
   }
  ],
  "parameters": [],
  "policies": [],
  "queues": [],
  "exchanges": [],
  "bindings": []
}
