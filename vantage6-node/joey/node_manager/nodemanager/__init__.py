"""Nodemanager
Module to manage dockerized ppdli node instances. 

Besides managing docker containers, it is also responsible for 
maintaining the configuration files. These configuration files are 
mounted by the node containers.  

Managing dockerized nodes:
* start node instance (node start) 
* stop node instance (node stop)
* list running instances (node ls --running)
* show node output (node inspect)

Managing configuration file:
* create (node create)
* update (node update)
* delete (node delete)
* list (node ls --all)
* files (node config files)
"""
import click
import docker
import os
import time

import logging

from colorama import init
init()

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

log = logging.getLogger("__init__")
log.setLevel(logging.DEBUG)

@click.command(name="start")
def start_container():
    # client = docker.APIClient()
    client = docker.DockerClient()
    
    # create network for the 'master' container. The master container
    # can create a network for its children by internally speaking to the
    # deamon...
    # master_network = client.networks.create("isolated", 
    #     driver="bridge", 
    #     scope="local",
    #     internal=True
    # )
    
    # outside_network = client.networks.create("outside", 
    #     driver="bridge", 
    #     scope="local",
    # )
    outside_network = client.networks.get("outside")

    # create data volume
    # volume = client.volumes.create("data")
    volume = client.volumes.get("data")
    
    # creating mount from host machine into the slave container
    # everything that is mounted in the /mnt/data folder will be 
    # stored in a docker-volume which can be accessed by the algorithms.
    mounts = [
        # TODO this needs to be OS independant
        docker.types.Mount(
            "/var/run/docker.sock", 
            "//var/run/docker.sock", 
            type="bind"
        ),
        docker.types.Mount(
            "/mnt/data/one.txt",
            "C:\data\one.txt",
            type="bind"
        )
    ]

    # Why //var/run/docker.sock exists on windows:
    # https://stackoverflow.com/questions/36765138/bind-to-docker-socket-on-windows
    log.info("starting container")
    container = client.containers.run("test-master", 
        detach=True,
        mounts=mounts,
        network="isolated",
        volumes={"data": {"bind": "/mnt/data", "mode": "rw"}}
    )

    # attach master container to have internet connection
    outside_network.connect(container)

    
    log.info("Wainting for master log----")
    while True:
        print(container.logs().decode("ascii"))
        time.sleep(1)
        if container.status == "exited":
            break
