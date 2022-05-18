<h1 align="center">
  <br>
  <a href="https://vantage6.ai"><img src="https://github.com/IKNL/guidelines/blob/master/resources/logos/vantage6.png?raw=true" alt="vantage6" width="350"></a>
</h1>

<h3 align=center> A privacy preserving federated learning solution</h3>
<h3 align="center">

<!-- Badges go here-->

</h3>

<p align="center">
  <a href="#books-documentation">Documentation</a> •
  <a href="#gift_heart-contributing">Contributing</a> •
  <a href="#black_nib-references">References</a>
</p>

-----------------------------------------------------------------------------------------------------
This repository is part of **vantage6**, our **privacy preserving federated learning infrastructure for secure insight exchange**, and contains all the **vantage6** infrastructure source/ code. Please visit our [website (vantage6.ai)](https://vantage6.ai) to learn more!

## :books: Documentation
This repository is home to 4 PyPi packages:

* [vantage6](https://pypi.org/project/vantage6) -> _CLI for managing node and server instances_
* [vantage6-client](https://pypi.org/project/vantage6-client) -> _Python client for interacting with the vantage6-server_
* [vantage6-node](https://pypi.org/project/vantage6-node) -> _Node application package_
* [vantage6-server](https://pypi.org/project/vantage6-server) -> _Server application package_

**Note that when using vantage6 you do not install the _server_ and _node_ packages. These are delivered to you in Docker images.**

Two docker images are published which contain the Node and Server applications:

* `harbor2.vantage6.ai/infrastructure/node:VERSION`
* `harbor2.vantage6.ai/infrastructure/server:VERSION`

These docker images are used by the _vantage6 CLI_ package, to install this package:

`pip install vantage6`

This will install the CLI which enables you to use the commands:

* `vnode CMD [OPTIONS]`
* `vserver CMD [OPTIONS]`

You can find more (user) documentation at [Gitbook (docs.vantage6.ai)](https://docs.vantage6.ai). If you have any questions, suggestions or just want to chat about federated learning: join our [Dircord (https://discord.gg/yAyFf6Y)](https://discord.gg/yAyFf6Y) channel.

## :gift_heart: Contributing
We hope to continue developing, improving, and supporting **vantage6** with the help of the federated learning community. If you are interested in contributing, first of all, thank you! Second, please take a look at our [contributing guidelines](https://docs.vantage6.ai/how-to-contribute/how-to-contribute)

## :black_nib: References
If you are using **vantage6**, please cite this repository as well as the accompanying paper as follows:

> - Frank Martin, Melle Sieswerda, Hasan Alradhi, et al. vantage6. Available at https://doi.org/10.5281/zenodo.3686944. Accessed on [MONTH, 20XX].
> - Arturo Moncada-Torres, Frank Martin, Melle Sieswerda, Johan van Soest, Gijs Gelijnse. VANTAGE6: an open source priVAcy preserviNg federaTed leArninG infrastructurE for Secure Insight eXchange. AMIA Annual Symposium Proceedings, 2020, p. 870-877. [[BibTeX](https://arturomoncadatorres.com/bibtex/moncada-torres2020vantage6.txt), [PDF](https://vantage6.ai/vantage6/)]

-----------------------------------------------------------------------------------------------------
<p align="center">
  <a href="https://vantage6.ai">vantage6.ai</a> •
  <a href="https://discord.gg/yAyFf6Y">Discord</a> •
  <a href="https://vantage6.discourse.group/">Discourse</a> •
  <a href="https://docs.vantage6.ai">User documentation</a> •
</p>
