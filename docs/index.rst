
.. include:: <isonum.txt>
.. _introduction:

Introduction
============
This section will describe the community, the overall architecture of the
platform and explains how this documentation space is organized.


Overview
--------
This documentation space consists of the following main sections:

* **Introduction** |rarr| *You are here now*
* :doc:`/user-documentation/index` |rarr| *Install and use vantage6-servers,
  -nodes or -clients*
* :doc:`/technical-documentation/index` (Under construction) |rarr|
  *Implementation details of the vantage6 platform*
* :doc:`/devops/index` |rarr| *How to collaborate on the development of the
  vantage6 infrastructure*
* :doc:`/algorithms/index` |rarr| *Develop algorithms that are compatible with
  vantage6*
* :doc:`/glossary` |rarr| *A dictionary of common terms used in these docs*
* :doc:`/release_notes` |rarr| *Log of what has been released and when*


Resources
---------

**Documentation**

* `docs.vantage6.ai <https://docs.vantage6.ai>`_ |rarr| *This documentation.*
* `vantage6.ai <https://vantage6.ai>`_ |rarr| *vantage6 project website*
* `Academic papers <https://vantage6.ai/vantage6/>`_ |rarr|
  *Technical insights into vantage6*

**Source code**

* `vantage6 <https://github.com/vantage6/vantage6>`_ |rarr| *Contains all*
  *components (and the python-client).*
* `Planning <https://github.com/orgs/vantage6/projects>`_ |rarr| *Contains all
  features, bugfixes and feature requests we are working on. To submit one
  yourself, you can create a*
  `new issue <https://github.com/vantage6/vantage6/issues>`_.

**Community**

* `Discord <https://discord.gg/yAyFf6Y>`_  |rarr| *Chat with the vantage6
  community*
* :ref:`Community meetings <Community Planning>` |rarr| *Bi-monthly developer
  community meeting*


What is vantage6?
-----------------
Vantage6 stands for pri\ **va**\ cy preservi\ **n**\ g
federa\ **t**\ ed le\ **a**\ rnin\ **g** infrastructur\ **e** for
\ **s**\ ecure \ **i**\ nsight e\ **x**\ change.

Watch this `video <https://youtu.be/HVHvlkAeuD0>`_ for a quick introduction.

.. todo insert the video above directly into docs (requires sphinx extension)

The project is inspired by the `Personal Health Train <https://pht.health-ri.nl/>`_
(PHT) concept. In this analogy vantage6 is the *tracks* and *stations*.
Compatible algorithms are the *trains*, and computation tasks are the *journey*.
Vantage6 is completely open source under the
`Apache License <https://github.com/IKNL/vantage6/blob/master/LICENSE>`_.

What vantage6 does:

* delivering algorithms to data stations and collecting their results
* managing users, organizations, collaborations, computation tasks and their
  results
* providing control (security) at the data-stations to their owners

What vantage6 does *not* (yet) do:

* formatting the data at the data station
* aligning data across the data stations (for the vertical partitioned use
  case)

The vantage6 infrastructure is designed with three fundamental functional
aspects of federated learning.

1. **Autonomy**. All involved parties should remain independent and autonomous.
2. **Heterogeneity**. Parties should be allowed to have differences in hardware
   and operating systems.
3. **Flexibility**. Related to the latter, a federated learning infrastructure
   should not limit the use of relevant data.


.. _architectureoverview:

Architecture
------------

In vantage6, a **client** can pose a question to the **server**, which is then
delivered as an **algorithm** to the **node** (:numref:`architecture-figure`).
When the algorithm completes, the node sends the results back to the client via
the server. An algorithm may be enabled to communicate directly with twin
algorithms running on other nodes.

.. _architecture-figure:
.. figure:: /images/architecture-overview.png
   :alt: Architecture overview
   :align: center

   Vantage6 has a client-server architecture. (A) The client is used by the
   researcher to create computation requests. It is also used to manage users,
   organizations and collaborations. (B) The server contains users,
   organizations, collaborations, tasks and their results. (C) The nodes have
   access to data and handle computation requests from the server.

Conceptually, vantage6 consists of the following parts:

* A (central) **server** that coordinates communication with clients and nodes.
  The server is in charge of processing tasks as well as handling
  administrative functions such as authentication and authorization.
* One or more **node(s)** that have access to data and execute algorithms
* **Users** (i.e. researchers or other applications) that request computations
  from the nodes via the client
* **Organizations** that are interested in collaborating. Each user belongs to
  one of these organizations.
* A **Docker registry** that functions as database of algorithms

On a technical level, vantage6 may be seen as a container
orchestration tool for privacy preserving analyses. It deploys a network of
containerized applications that together ensure insights can be exchanged
without sharing record-level data.

-------------------------------------------------------------------------------

Index
=====

.. toctree::
   :numbered: 3
   :maxdepth: 4

   self
   user-documentation/index
   algorithms/index
   devops/index
   glossary
..  technical-documentation/index

.. toctree::
   :maxdepth: 2

   release_notes
   partners
