<h1 align="center">
  <br>
  <a href="https://vantage6.ai"><img src="https://github.com/IKNL/guidelines/blob/master/resources/logos/vantage6.png?raw=true" alt="vantage6" width="350"></a>
</h1>

<h3 align=center> A privacy preserving federated learning solution</h3>
<h3 align="center">

[![Coverage Status](https://coveralls.io/repos/github/IKNL/vantage6-node/badge.svg?branch=master)](https://coveralls.io/github/IKNL/vantage6-node?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/0f03092824814c5797224884fb65f048)](https://www.codacy.com/gh/IKNL/vantage6-node?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=IKNL/vantage6-node&amp;utm_campaign=Badge_Grade)
[![PyPI version](https://badge.fury.io/py/vantage6-client.svg)](https://badge.fury.io/py/vantage6-client)
[![Build Status](https://api.travis-ci.org/IKNL/vantage6-node.svg?branch=master)](https://travis-ci.org/IKNL/vantage6-node)
<!--[![PyPI version](https://badge.fury.io/py/ppDLI.svg)](https://badge.fury.io/py/ppDLI)-->

</h3>

<p align="center">
  <a href="#books-documentation">Documentation</a> •
  <a href="#cd-installation">Installation</a> •
  <a href="#hatching_chick-how-to-use">How To Use</a> •
  <a href="#gift_heart-contributing">Contributing</a> •
  <a href="#black_nib-references">References</a>
</p>

-----------------------------------------------------------------------------------------------------
This repository is part of **vantage6**, our **priVAcy preserviNg federaTed leArninG infrastructurE for Secure Insight eXchange**. Other repositories include:

*   [vantage6](https://github.com/iknl/vantage6)
*   [vantage6-common](https://github.com/iknl/vantage6-common)
*   [vantage6-server](https://github.com/iknl/vantage6-server)
*   vantage6-node (you are here)
*   [vantage6-client](https://github.com/iknl/vantage6-client)
*   [vantage6-UI](https://github.com/IKNL/Vantage6-UI)
*   [vantage6-master](https://github.com/iknl/vantage6-master)

## :books: Documentation
The following is a short cheat sheet of how to setup a **vantage6** node. For a more detailed, comprehensive guide, please refer to our [website `https://vantage6.ai`](https://vantage6.ai) and the official [documentation: `https://docs.vantage6.ai/`](https://docs.vantage6.ai/).

## :cd: Installation
This repository contains the code for a **vantage6** node. Installation can be done in two different ways:

### Option 1 - Directly from `pypi`
```bash
pip install vantage6-node
```
### Option 2 - From this repository
```bash
# Clone repository
git clone https://github.com/iknl/vantage6-node

# Go into the repository
cd vantage6-node

# install vantage6-node and dependencies
pip install -e .
```

## :hatching_chick: How to use
```bash
# Show the available commands
vnode --help

# Create a new configuration
vnode new [OPTIONS]

# start a configuration
vnode start [OPTIONS]

# See where usefull files are located
vnode files [OPTIONS]

# Stop one or more nodes
vnode stop [OPTIONS]

# Attach the log output of a node to the console
vnode attach [OPTIONS]

```
## :gift_heart: Contributing
We hope to continue developing, improving, and supporting **vantage6** with the help of the federated learning community. If you are interested in contributing, first of all, thank you! Second, please take a look at our [contributing guidelines](https://docs.vantage6.ai/how-to-contribute/how-to-contribute)

## :lock_with_ink_pen: Data Protection Impact Assessment
Deploying Federated Learning solutions in real life often requires careful analysis and approval of a variety of legal entities. As part of these processes, we at IKNL have written a [Data Protection Impact Assessment (DPIA), which you can find here](https://vantage6.ai/data-protection-impact-assessment-dpia/). Please note that this DPIA was executed by IKNL and is specific for our situation. It can be used as an example by other organizations, but it cannot be used verbatim.

## :black_nib: References
If you are using **vantage6**, please cite this repository as well as the accompanying paper as follows:

> - Frank Martin, Melle Sieswerda, Hasan Alradhi, et al. vantage6. Available at https://doi.org/10.5281/zenodo.3686944. Accessed on [MONTH, 20XX].
> - Arturo Moncada-Torres, Frank Martin, Melle Sieswerda, Johan van Soest, Gijs Gelijnse. VANTAGE6: an open source priVAcy preserviNg federaTed leArninG infrastructurE for Secure Insight eXchange. AMIA Annual Symposium Proceedings, 2020, p. 870-877. [[BibTeX](https://arturomoncadatorres.com/bibtex/moncada-torres2020vantage6.txt), [PDF](https://vantage6.ai/vantage6/)]

-----------------------------------------------------------------------------------------------------
<p align="center">
  <a href="https://github.com/IKNL/vantage6">vantage6</a> •
  <a href="https://github.com/IKNL/vantage6-common">Common</a> •
  <a href="https://github.com/IKNL/vantage6-server">Server</a> •
  <a>Node</a> •
  <a href="https://github.com/IKNL/vantage6-client">Client</a> •
  <a href="https://github.com/IKNL/Vantage6-UI">UI</a> •
  <a href="https://github.com/IKNL/vantage6-master">Master</a>
</p>
