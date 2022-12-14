
.. include:: <isonum.txt>
.. _introduction:

Introduction
============

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


Overview of this documentation
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


Vantage6 resources
---------

This is a - non-exhaustive - list of vantage6 resources.

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


-------------------------------------------------------------------------------

Index
=====

.. toctree::
   :maxdepth: 4

   self
   introduction/concepts

.. toctree::
   :numbered: 3
   :maxdepth: 4

   install/index
   use/index
   algorithms/index
   devops/index
   glossary
..  technical-documentation/index

.. toctree::
   :maxdepth: 2

   release_notes
   partners
