<img src="https://github.com/IKNL/guidelines/blob/master/resources/logos/vantage6.png?raw=true" width=200 align="right">

[![Coverage Status](https://coveralls.io/repos/github/IKNL/vantage6-node/badge.svg?branch=master)](https://coveralls.io/github/IKNL/vantage6-node?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/0f03092824814c5797224884fb65f048)](https://www.codacy.com/gh/IKNL/vantage6-node?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=IKNL/vantage6-node&amp;utm_campaign=Badge_Grade)
<!--[![PyPI version](https://badge.fury.io/py/ppDLI.svg)](https://badge.fury.io/py/ppDLI)-->[![Build Status](https://api.travis-ci.org/IKNL/vantage6-node.svg?branch=master)](https://travis-ci.org/IKNL/vantage6-node)

# Introduction
The growing complexity of cancer diagnosis and treatment requires data sets that are larger than currently available in a single hospital or even in cancer registries. However, sharing patient data is difficult due to patient privacy and data protection needs. Federated learning technology has the potential to overcome these limitations. In this approach, organizations can collaborate by exchanging aggregated data and/or statistics while keeping the underlying data safely on site and undisclosed. This repository contains software (and instructions) to setup a federated learning infrastructure.

For an overview of the architecture and information on how to use the infrastructure, please see [https://vantage6.ai](https://vantage6.ai). For documentation, please see [https://docs.distributedlearning.ai/](https://docs.distributedlearning.ai/).

## Hardware and software requirements
Running a node/site requires a (virtual) machine that has:
* Python 3.6+ and the ppdli package installed (`pip install vantage6-node`)
* Docker CE installed (the user running the node software needs to have the proper permissions to perform docker commands)
* Access to a local data store
* Access to the internet and/or central server

## Installation
See the [documentation](https://docs.distributedlearning.ai/) for detailed instructions on how to install the server and nodes. 
