<img src="https://github.com/IKNL/guidelines/blob/master/resources/logos/vantage6.png?raw=true" width=200 align="right">

[![Coverage Status](https://coveralls.io/repos/github/IKNL/vantage6-server/badge.svg?branch=master)](https://coveralls.io/github/IKNL/vantage6-server?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/707833fa47a94393b3f8ab9f2c598034)](https://www.codacy.com/gh/IKNL/vantage6-server?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=IKNL/vantage6-server&amp;utm_campaign=Badge_Grade)
[![Build Status](https://travis-ci.org/IKNL/ppDLI.svg?branch=master)](https://travis-ci.org/IKNL/vantage6-server)
<!--[![PyPI version](https://badge.fury.io/py/ppDLI.svg)](https://badge.fury.io/py/ppDLI) -->

# Introduction
The growing complexity of cancer diagnosis and treatment requires data sets that are larger than currently available in a single hospital or even in cancer registries. However, sharing patient data is difficult due to patient privacy and data protection needs. Federated learning technology has the potential to overcome these limitations. In this approach, organizations can collaborate by exchanging aggregated data and/or statistics while keeping the underlying data safely on site and undisclosed. This repository contains software (and instructions) to setup a federated learning infrastructure.

For an overview of the architecture and information on how to use the infrastructure, please see [https://vantage6.ai](https://vantage6.ai). For documentation, please see [https://docs.distributedlearning.ai/](https://docs.distributedlearning.ai/).

## Hardware and software requirements
Running the central server requires a (virtual) machine that:
* is accessible from the internet
* has Python 3.6+ and the ppdli package installed (`pip install vantage6-server`)

## Installation
See the [documentation](https://docs.distributedlearning.ai/) for detailed instructions on how to install the server and nodes. 
