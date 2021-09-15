
<h1 align="center">
  <br>
  <a href="https://vantage6.ai"><img src="https://github.com/IKNL/guidelines/blob/master/resources/logos/vantage6.png?raw=true" alt="vantage6" width="350"></a>
</h1>

<h3 align=center> A privacy preserving federated learning solution</h3>
<h3 align="center">

[![PyPI version](https://badge.fury.io/py/vantage6.svg)](https://badge.fury.io/py/vantage6)
[![CI](https://github.com/IKNL/vantage6/actions/workflows/ci.yaml/badge.svg)](https://github.com/IKNL/vantage6/actions/workflows/ci.yaml)
[![Coverage Status](https://coveralls.io/repos/github/IKNL/vantage6/badge.svg?branch=master)](https://coveralls.io/github/IKNL/vantage6?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/6ea309088ccd48febd41bd1176a9db55)](https://www.codacy.com/gh/IKNL/vantage6?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=IKNL/vantage6&amp;utm_campaign=Badge_Grade)
[![DOI](https://zenodo.org/badge/120275991.svg)](https://zenodo.org/badge/latestdoi/120275991)

</h3>

<p align="center">
  <a href="#pray-motivation">Motivation</a> •
  <a href="#books-documentation">Documentation</a> •
  <a href="#cd-installation">Installation</a> •
  <a href="#hatching_chick-how-to-use">How To Use</a> •
  <a href="#gift_heart-contributing">Contributing</a> •
  <a href="#black_nib-references">References</a>
</p>

-----------------------------------------------------------------------------------------------------
This repository is part of **vantage6**, our **priVAcy preserviNg federaTed leArninG infrastructurE for Secure Insight eXchange**. Other repositories include:

* [vantage6-common](https://github.com/iknl/vantage6-common)
* [vantage6-server](https://github.com/iknl/vantage6-server)
* [vantage6-node](https://github.com/iknl/vantage6-node)
* [vantage6-client](https://github.com/iknl/vantage6-client)
* [vantage6-UI](https://github.com/IKNL/Vantage6-UI)
* [vantage6-master](https://github.com/iknl/vantage6-master)

## :pray: Motivation
The growing complexity of cancer diagnosis and treatment requires data sets that are larger than currently available in a single hospital or even in cancer registries. However, sharing patient data is often difficult due to patient privacy and data protection needs. Federated learning technology has the potential to overcome these limitations. In this approach, organizations can collaborate by exchanging aggregated data and/or statistics while keeping the underlying data safely on site and undisclosed. This repository contains software (and instructions) to setup a federated learning infrastructure using vantage6.

## :books: Documentation
The following is a short cheat sheet of how to install and use vantage6. For a more detailed, comprehensive guide, please refer to our [website `https://vantage6.ai`](https://vantage6.ai) and the official [documentation: `https://docs.vantage6.ai/`](https://docs.vantage6.ai/).

## :cd: Installation
This repository contains a command-line-interface (CLI) to manage Docker versions of servers and nodes. If you are setting up either of them, you only need to install this repository. This can be done in two different ways:

### Option 1 - Directly from `pypi`
```bash
pip install vantage6
```
### Option 2 - From this repository
```bash
# Clone repository
git clone https://github.com/iknl/vantage6

# Go into the repository
cd vantage6

# install vantage6 and dependencies
pip install -e .
```

## :hatching_chick: How to use
### Node
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

### Server
```bash
# Show available commands
vserver --help

# Create new server
vserver new [OPTIONS]

# Start a server
vserver start [OPTIONS]

# Attach the log output of a server to the console
vserver attach [OPTIONS]

# Batch import multiple entities into the server
vserver import PATH [OPTIONS]

# Show usefull files per server
vserver files [OPTIONS]

# Stop one ore more
vserver stop [OPTIONS]
```
## :gift_heart: Contributing
We hope to continue developing, improving, and supporting **vantage6** with the help of the federated learning community. If you are interested in contributing, first of all, thank you! Second, please take a look at our [contributing guidelines](https://docs.vantage6.ai/how-to-contribute/how-to-contribute)

## :lock_with_ink_pen: Data Protection Impact Assessment
Deploying Federated Learning solutions in real life often requires careful analysis and approval of a variety of legal entities. As part of these processes, we at IKNL have written a [Data Protection Impact Assessment (DPIA), which you can find here](https://vantage6.ai/data-protection-impact-assessment-dpia/). Please note that this DPIA was executed by IKNL and is specific for our situation. It can be used as an example by other organizations, but it cannot be used verbatim.

## :black_nib: References
If you are using **vantage6**, please cite this repository as well as the accompanying paper as follows:

> - Frank Martin, Melle Sieswerda, Hasan Alradhi, et al. vantage6. Available at
https://doi.org/10.5281/zenodo.3686944. Accessed on [MONTH, 20XX].
> - Arturo Moncada-Torres, Frank Martin, Melle Sieswerda, Johan van Soest, Gijs Gelijnse. VANTAGE6: an open source priVAcy preserviNg
federaTed leArninG infrastructurE for Secure Insight eXchange. AMIA Annual Symposium Proceedings, 2020, p. 870-877. [[BibTeX](https://arturomoncadatorres.com/bibtex/moncada-torres2020vantage6.txt), [PDF](https://vantage6.ai/vantage6/)]

-----------------------------------------------------------------------------------------------------
<p align="center">
  <a>vantage6</a> •
  <a href="https://github.com/IKNL/vantage6-common">Common</a> •
  <a href="https://github.com/IKNL/vantage6-server">Server</a> •
  <a href="https://github.com/IKNL/vantage6-node">Node</a> •
  <a href="https://github.com/IKNL/vantage6-client">Client</a> •
  <a href="https://github.com/IKNL/Vantage6-UI">UI</a> •
  <a href="https://github.com/IKNL/vantage6-master">Master</a>
</p>
