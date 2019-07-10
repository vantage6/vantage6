"""Create a docker image from this file called: `test-master`.

Has access to both the internal (isolated) and external network (outside).
"""
import time 
import logging
import docker
import requests

from shutil import copyfile
from pathlib import Path

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

log = logging.getLogger("main")
log.setLevel(logging.DEBUG)

log.info("master - Connecting to docker-host")

# Create connection to docker-deamon
client = docker.DockerClient(base_url="unix://var/run/docker.sock")

# create master container
log.info("master - master read mount...")
time.sleep(1)
with open("/mnt/data/one.txt") as f:
    log.info(f.read())

# create container and pass: docker-deamon socker, network and data-volume.
log.info("master - Creating container")
container = client.containers.run("test-slave", 
    detach=True,
    mounts=[
        # TODO this needs to be OS independant
        docker.types.Mount(
            "/var/run/docker.sock",
            "//var/run/docker.sock",
            type="bind"
        )
    ],
    network="isolated",
    # mount the docker-volume `data` and bind it to /mnt/data
    volumes={"data":{"bind": "/mnt/data", "mode": "rw"}}
)

# checking internet connection
log.info("master - master attemt to connect to the internet")
res = requests.get("https://facebook.com")
log.info(f"stat={res.status_code}")

# keep reading slave log
log.info("master - Reading log files from container container")
while True:
    time.sleep(2)
    print(container.logs().decode("ascii"))
    log.info("master - Sleeping 2 seconds")
