
.. include:: <isonum.txt>
.. _introduction:

Introduction
============
This section will describe the community, the overall architecture of the
platform and explains how this documentation space is organized.


Index
-----
This documentation space consists of 7 main sections:

* **Introduction** |rarr| *You are here now*
* :doc:`/user-documentation/index` |rarr| *Install and use vantage6-servers,
  -nodes or -clients*
* :doc:`/technical-documentation/index` |rarr| Implementation details of the
  vantage6 platform*
* :doc:`/devops/index` |rarr| *How to collaborate on the development of the
  vantage6 infrastructure*
* :doc:`/algorithms/index` |rarr| *Develop algorithms that are compatible with
  vantage6*
* :doc:`/release_notes` |rarr| changelog to the source code
* :doc:`/glossary`


Resources
---------

**Documentation**

* `docs.vantage6.ai <https://docs.vantage6.ai>`_ |rarr| *this documentation.*
* `vantage6.ai <https://vantage6.ai>`_ |rarr| *vantage6 project website*
* `academic papers <https://distributedlearning.ai/vantage6/>`_ |rarr|
  *technical insights into vantage6*

**Source code**

* `vantage6 <https://github.com/vantage6/vantage6>`_ |rarr| *contains all*
  *components (and the python-client).*
* `Planning <https://github.com/orgs/vantage6/projects>`_ |rarr| contains all
  features, bugfixes and feature request we are working on. To submit one
  yourself, you can create a `new issue <https://github.com/vantage6/vantage6/issues>`_.

**Community**

* `Discord <https://discord.gg/yAyFf6Y>`_  |rarr| chat with the vantage6
  community
* :ref:`Community meetings <Community Planning>` |rarr| bi-monthly developer
  community meeting


What is vantage6?
-----------------
Vantage6 stands for pri\ **va**\ cy preservi\ **n**\ g
federa\ **t**\ ed le\ **a**\ rnin\ **g**\ infrastructur\ **e** for
\ **s**\ ecure \ **i**\ nsight e\ **x**\ change.  A more technical explanation
would be: *a container orchastration tool for privacy preserving analysis*.
Watch this `video <https://youtu.be/HVHvlkAeuD0>`_ for a quick introduction.

The project is inspired by the `Personal Health Train <https://pht.health-ri.nl/>`_
(PHT) concept. In this analogy vantage6 is the *tracks* and *stations*.
Compatible algorithms are the *trains*, and computation tasks are the *journey*.
Vantage6 is completely open source under the
`Apache License <https://github.com/IKNL/vantage6/blob/master/LICENSE>`_.

vantage6 is here for:

* delivering algorithms to data stations and collecting their results
* managing users, organizations, collaborations, computation tasks and their
  results
* providing control (security) at the data-stations to their owners

vantage6 is *not* (yet):

* formatting the data at the data station
* aligning data across the data stations (for the vertical partitioned use
  case)

vantage6 is designed with three fundamental functional aspects of Federated
learning.

1. **Autonomy**. All involved parties should remain independent and autonomous.
2. **Heterogeneity**. Parties should be allowed to have differences in hardware
   and operating systems.
3. **Flexibility**. Related to the latter, a federated learning infrastructure
   should not limit the use of relevant data.

Architecture
------------

Vantage6 uses both a client-server and peer-to-peer model. In the figure below
the **client** can pose a question to the **server**, the question is then
delivered as an algorithm to the node. When the algorithm completes, the
results are sent back to the client via the server. An algorithm can
communicate directly with other algorithms that run on other nodes if required.

.. figure:: /images/architecture-overview.png
   :alt: Architecture overview
   :align: center

   Vantage6 has a client-server architecture. The Researcher interacts with
   the server to create computation requests and to manage user accounts,
   organizations and collaborations. The Server contains users, organizations,
   collaborations, tasks and their results. The Node has access to data and
   handles computation requests from the server.

The server is in charge of processing the tasks as well as of handling
administrative functions such as authentication and authorization.
Conceptually, vantage6 consists of the following parts:

* A (central) **server** that coordinates communication with clients and nodes
* One or more **node(s)** that have access to data and execute algorithms
* **Organizations** that are interested in collaborating;
* **Users** (i.e. researchers or other applications) that request computations
  from the nodes
* A **Docker registry** that functions as database of algorithms


Partners
--------

Contact us via the `Discourse <https://vantage6.discourse.group/>`_ forum!

.. container:: block-image

    .. image:: /images/iknl-logo.jpg
        :alt: IKNL logo
        :align: left

* Anja van Gestel
* Bart van Beusekom
* Frank Martin
* Hasan Alradhi
* Melle Sieswerda
* Gijs Geleijnse

.. container:: block-image

    .. image:: /images/escience-center-logo.png
        :alt: eScience center logo
        :align: center

* Djura Smits
* Lourens Veen

.. container:: block-image

    .. image:: /images/maastro-logo.png
        :alt: eScience center logo
        :align: center

* Johan van Soest

**Would you like to contribute?** Check out
:ref:`how to contribute! <Contribute>`

