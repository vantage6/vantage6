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

## Installation
See the [wiki](https://github.com/IKNL/pytaskmanager/wiki) for detailed instructions on how to install the server and nodes. 


