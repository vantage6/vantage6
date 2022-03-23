import docker
import json
import os
import shutil
import base64
import hashlib

from pathlib import Path
from typing import Dict

from vantage6.common.globals import APPNAME
from vantage6.common.docker_addons import remove_container_if_exists
from vantage6.cli.context import ServerContext
from vantage6.server.rabbitmq.definitions import RABBITMQ_DEFINITIONS

RABBIT_IMAGE = 'rabbitmq:3-management'
RABBIT_CONFIG = 'rabbitmq.config'
RABBIT_DIR = 'rabbitmq'


class RabbitMQManager:
    """
    Manages the RabbitMQ docker container
    """
    def __init__(self, ctx: ServerContext, queue_uri: str) -> None:
        """
        Parameters
        ----------
        ctx: ServerContext
            Configuration object
        queue_uri: str
            URI where the RabbitMQ instance should be running
        """
        self.ctx = ctx
        self.queue_uri = queue_uri
        self.docker = docker.from_env()

        self.rabbit_container_name = f'{APPNAME}_{ctx.name}_rabbitmq'

        self.start_queue()

    def start_queue(self):
        """
        Start a docker container which runs a RabbitMQ queue
        """
        # get volumes which contain
        volumes = self._get_volumes()

        # expose port 5672 inside the container as port 3333 on the host, and
        # same for 15672 in container to 8080 on host
        ports = {
            '5672/tcp': 5672,
            # TODO this is for the management tool, do we keep this?
            '15672/tcp': 8080
        }

        # if a RabbitMQ container is already running, kill and remove it
        remove_container_if_exists(
            docker_client=self.docker, name=self.rabbit_container_name
        )

        self.rabbit_container = self.docker.containers.run(
            name=self.rabbit_container_name,
            image=RABBIT_IMAGE,
            volumes=volumes,
            ports=ports,
            detach=True,
            restart_policy={"Name": "always"},
            hostname=f'{APPNAME}-{self.ctx.name}-rabbit'
        )

    def _get_volumes(self) -> Dict:
        """
        Prepare the volumes for the RabbitMQ container. The RabbitMQ should
        set up the right vhost and users to allow the server to communicate
        with RabbitMQ as configured.
        """
        # default RabbitMQ configuration: replace the user/password with the
        # credentials from the configuraiton
        rabbit_settings = self.ctx.config.get('rabbitmq')
        rabbit_definitions = RABBITMQ_DEFINITIONS
        rabbit_definitions['users'][0]['name'] = rabbit_settings['user']
        rabbit_definitions['permissions'][0]['user'] = rabbit_settings['user']
        rabbit_definitions['users'][0]['password_hash'] = \
            self._get_hashed_pw(rabbit_settings['password'])

        # write the RabbitMQ configuration to file(s)
        definitions_filepath = Path(self.ctx.data_dir / 'definitions.json')
        with open(definitions_filepath, 'w') as f:
            json.dump(rabbit_definitions, f, indent=2)
        rabbit_conf = \
            Path(os.path.dirname(os.path.realpath(__file__))) / RABBIT_CONFIG
        # conf_filepath = Path(self.ctx.data_dir / 'rabbitmq.conf')
        shutil.copyfile(rabbit_conf, self.ctx.data_dir / RABBIT_CONFIG)

        # check if a directory for persistent RabbitMQ storage exists,
        # otherwise create it
        rabbit_data_dir = self.ctx.data_dir / RABBIT_DIR
        if not os.path.exists(rabbit_data_dir):
            os.makedirs(rabbit_data_dir)

        return {
            definitions_filepath: {
                'bind': '/etc/rabbitmq/definitions.json', 'mode': 'ro'
            },
            self.ctx.data_dir / 'rabbitmq.config': {
                'bind': '/etc/rabbitmq/rabbitmq.config', 'mode': 'ro'
            },
            rabbit_data_dir: {
                'bind': '/var/lib/rabbitmq', 'mode': 'rw'
            }
        }

    def _get_hashed_pw(self, pw):
        """ Hash a user-defined password for RabbitMQ """

        # Generate a random 32 bit salt:
        salt = os.urandom(4)

        # Concatenate that with the UTF-8 representation of the password
        tmp0 = salt + pw.encode('utf-8')

        # Take the SHA256 hash and get the bytes back
        tmp1 = hashlib.sha256(tmp0).digest()

        # Concatenate the salt again:
        salted_hash = salt + tmp1

        # convert to base64 encoding:
        pass_hash = base64.b64encode(salted_hash)
        return pass_hash.decode('utf-8')
