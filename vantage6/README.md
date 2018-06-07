# Table of Contents
* [Introduction](#introduction)
* [Architecture of the infrastructure](#architecture-of-the-infrastructure)
* [Using the infrastructure](#using-the-infrastructure)
  * [Process flow](#process-flow)
  * [Hardware and software requirements](#hardware-and-software-requirements)
  * [Installation](#installation)
  
# Introduction
The growing complexity of cancer diagnosis and treatment requires data sets that are larger than currently available in a single hospital or even in cancer registries. However, sharing patient data is difficult due to patient privacy and data protection needs. Privacy preserving distributed learning technology has the potential to overcome these limitations. In this setting organizations can collaborate by exchanging aggregated data and/or statistics while keeping the underlying data safely on site and undisclosed. This repository contains software (and instructions) to setup a distributed learning infrastructure.

# Architecture of the infrastructure
 Conceptually, the infrastructure consists of three parts:

1. A central server that coordinates communication with the nodes
1. Multiple nodes 
1. A Docker registry

Each participating site runs a node. This node is configured to access a local data store. Researchers can upload "tasks" (computation requests) to the central server which are picked up by the nodes and executed. Afterwards the nodes return the results to the server. At that point a researcher can retrieve the results and combine them into a single result if he/she so chooses.

In order to support different working environments and provide researchers with as much flexibility as possible with respect to the tools they can use, the infrastructure is built on the concept of computation requests encapsulated in Docker images. This means the researcher is free to implement any application/script, embedded in a Docker image. The nodes only need to run the image and to provide the container with access to the data store in order to execute the computation. For some algorithms images are already available, for example the [distributed Cox Proportional Hazards](https://github.com/IKNL/dcoxph/) algorithm

![Systems overview](https://raw.githubusercontent.com/IKNL/pytaskmanager/master/img/systems_overview.png)


# Using the infrastructure
## Process flow
The following image illustrates how a researcher would use the infrastructure on a high level. For a more detailed example, see the GitHub repository for the [distributed Cox Proportional Hazards](https://github.com/IKNL/dcoxph/) algorithm.
![Process flow](https://raw.githubusercontent.com/IKNL/pytaskmanager/master/img/process_flow.png)

## Hardware and software requirements
Running the central server requires a (virtual) machine that:
* is accessible from the internet
* has Python 3 and the PyTaskManager package installed
* has Docker installed, and given rights to the user executing the client rights to perform docker commands

Running a node/site requires a (virtual) machine that has:
* Python 3 and the PyTaskManager package installed
* Docker CE installed (the user running the node software needs to have the proper permissions to perform docker commands)
* Access to a local data store
* Access to the internet and/or central server

## Installation
See the [wiki](https://github.com/IKNL/pytaskmanager/wiki) for detailed instructions on how to install the server and nodes. 


