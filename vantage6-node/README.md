[![PyPI version](https://badge.fury.io/py/ppDLI.svg)](https://badge.fury.io/py/ppDLI)
[![Build Status](https://travis-ci.com/IKNL/ppDLI.svg?branch=master)](https://travis-ci.com/IKNL/ppDLI)
# Introduction
The growing complexity of cancer diagnosis and treatment requires data sets that are larger than currently available in a single hospital or even in cancer registries. However, sharing patient data is difficult due to patient privacy and data protection needs. Privacy preserving distributed learning technology has the potential to overcome these limitations. In this setting organizations can collaborate by exchanging aggregated data and/or statistics while keeping the underlying data safely on site and undisclosed. This repository contains software (and instructions) to setup a distributed learning infrastructure.

For an overview of the architecture and information on how to use the infrastructure, please see [https://distributedlearning.ai](https://distributedlearning.ai).

## Hardware and software requirements
### Server
Running the central server requires a (virtual) machine that:
* is accessible from the internet
* has Python 3 and the PyTaskManager package installed

### Node
Running a node/site requires a (virtual) machine that has:
* Python 3 and the PyTaskManager package installed
* Docker CE installed (the user running the node software needs to have the proper permissions to perform docker commands)
* Access to a local data store
* Access to the internet and/or central server

Next to this registry, there is a node, which polls a central registry, to check for new tasks to execute. If a new task is available, the referenced container is pulled from the docker hub (e.g. `docker pull <container name>`) irrespective of whether it was pulled before. Afterwards, this container is executed (e.g. `docker run --rm -d <container name>`), with mounts for configuration files and output folders. Furthermore, the *internal* SPARQL endpoint URL is passed to the container as an environment variable (`$SPARQL_ENDPOINT=<url>`).

This means the researcher is free to implement any application/script, embedded in a docker container. Sites running the node are able to limit the docker containers being able to run on their system. It is possible to limit the user/organization which developed the container (e.g. only allowing the regular expression `myConsortium/.*:.*` of container images), or even on the repository level (e.g. `myConsortium/myImage:.*`).

# How to use it?

## Prerequisites

At the (hospital) site:

* A Windows Server 2012R2 (or higher) machine, or a unix machine supporting Docker
* Docker installed, and given rights to the user executing the node rights to perform docker commands
* Python 2.7 or 3 (tested on both)

At the central registry:

* A Windows Server 2012R2 (or higher) machine, or a unix machine supporting Docker
* Docker installed, and given rights to the user executing the node rights to perform docker commands
* Python 2.7 or 3 (tested on both)

## How to run?

At the central registry:

1. Please checkout this repository
2. Run the python script master/TaskMaster.py (`python master/TaskMaster.py`). The registry will now run at port 5000, and the output is shown at the console.

At the (hospital) sites:

1. Checkout this repository
2. Please adapt the config.json file to your site information, including the local URL to your internal SPARQL endpoint.
3. Run the python script node/runScript.py (`python node/runScript.py`)
4. **Optionally**: if you have a public IP address, you can also receive direct files (e.g. usefull if your site is a Trusted Third Party, and (encrypted) files are sent to you). To run this service, please execute the python script node/FileService.py (`python node/FileService.py`).

## How to build and run an algorithm?

The registry is based on REST commands. The docker containers are *only* needed for execution at the sites. As a researcher, this means you have to develop a docker container which can run on *every* site.

To merge results from all sites, and to run the *centralised* part of your analysis, you can develop a script on your own computer. This computer can retrieve the results from the registry, perform its calculations, and (optionally, in an iterative algorithm) post a new request to run an image on the contributing sites. This can also be the same Docker image, using an updated configuration file.

# How to contribute?
If you have any requests, you can fork this repository, develop the addition/change, and send a pull request. If you have a request for a change, please add it to the issue tracker (see "Issues" in the left navigation bar).

This readme and documentation still needs work, as the code for this infrastructure is still work in progress. If you have any question regarding use, please use the issue tracker as well. We might update the readme file accordingly, but also helps us to define where the need for help is.
