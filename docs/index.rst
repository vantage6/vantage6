.. include:: <isonum.txt>

Overview
========

What is vantage6?
-----------------

Vantage6 is a privacy-enhancing technology (PET) platform that allows organizations to
collaborate on data analysis tasks without sharing the data itself. Vantage6 is
open source and completely free to use.

.. raw:: html

   <iframe width="750" height="420" src="https://youtube.com/embed/HVHvlkAeuD0"
     frameborder="0"
     allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
     allowfullscreen>
   </iframe>

What vantage6 does:

* deliver algorithms to data stations and collecting their results
* manage users, organizations, collaborations, computation tasks and their
  results
* provide control (security) at the data stations to the data owners

The vantage6 infrastructure is designed with three fundamental functional
aspects of federated learning.

1. **Autonomy**. All involved parties should remain independent and autonomous.
2. **Heterogeneity**. Parties should be allowed to have differences in hardware
   and operating systems.
3. **Flexibility**. Related to the latter, a federated learning infrastructure
   should not limit the use of relevant data.


Overview of this documentation
------------------------------

This documentation space consists of the following main sections:

* **Overview** |rarr| *You are here now*
* :doc:`/introduction/introduction` |rarr| *Introduction to vantage6 concepts*
* :doc:`/introduction/quickstart` |rarr| *Quickstart guide - run vantage6 locally*
* :doc:`/user/index` |rarr| *How to use vantage6 as a researcher*
* :doc:`/node/index` |rarr| *How to install and configure vantage6 nodes*
* :doc:`/hub/index` |rarr| *How to configure and deploy the central vantage6 components*
* :doc:`/devops/index` |rarr| *How to collaborate on the development of vantage6*
* :doc:`/algorithms/index` |rarr| *Develop vantage6 algorithms*
* :doc:`/technical_reference/index` |rarr| *In-depth documentation of vantage6 features*
* :doc:`/api-docs/index` |rarr|
  *Documentation of the vantage6 infrastructure code*
* :doc:`/glossary` |rarr| *A dictionary of common terms used in these docs*
* :doc:`/release_notes` |rarr| *Log of what has been released and when*


Vantage6 resources
------------------

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
* :ref:`Community meetings <community-meetings>` |rarr| *Bi-monthly developer
  community meeting*


-------------------------------------------------------------------------------

Index
=====

.. toctree::
   :maxdepth: 4

   self
   introduction/introduction
   introduction/quickstart
   introduction/communitystore

.. toctree::
   :numbered: 3
   :maxdepth: 4

   user/index
   node/index
   hub/index
   algorithms/index
   devops/index
   technical_reference/index
   api-docs/index
   glossary

.. toctree::
   :maxdepth: 2

   release_notes
   partners
