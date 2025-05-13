Glossary
========

The following is a list of definitions used in vantage6.

**A**

-  **Algorithm**: a piece of code that performs a specific task.
-  **Algorithm store**: A repository of algorithms, which can be coupled to specific
   collaborations or all collaborations on a server.
-  **API**: Application Programming Interface, a set of routines, protocols, and tools
   for building software applications.
-  **Authentication**: the process of verifying the identity of a user.
-  **Authorization**: the process of verifying the permissions of a user.
-  **Autonomy:** the ability of a party to be in charge of the control and management of
   its own data.

**C**

-  **Central function**: The orchestration part of an algorithm that coordinates and
   aggregates results from partial functions.
-  **Child container**: A container created by an algorithm container to perform
   subtasks, typically a *federated function*
-  **Client**: A vantage6 user or application that uses the vantage6-server to run
   algorithms.
-  **Collaboration**: an agreement between two or more parties to participate in a study
   (i.e., to answer a research question).
-  **Container**: A lightweight, standalone, executable package of software that
   includes everything needed to run it.

**D**

-  **DataFrame**: A standardized representation of data in a session that can be used
   for computation tasks.
-  **Data Station**: A vantage6 *node* that has access to the local data.
-  **Distributed learning**: see *Federated Learning* and *Federated Analytics*
-  **Docker:** a platform that uses operating system virtualization to deliver software
   in packages called *containers*. It is worth noting that although they are often
   confused, `Docker containers are not virtual machines <https://www.docker.com/blog/containers-are-not-vms/>`__.
-  **Docker registry**: A repository of *images*. In vantage6, both algorithms and
   the infrastructure itself are stored as *images* in the *Docker registry*. Images
   are used to create *containers*.

**E**

-  **End-to-end encryption**: A method of encoding data so that it can only be decoded
   by the intended recipient. In vantage6, end-to-end encryption is used to encrypt
   data in transit between the vantage6-server and the vantage6-node and between
   the vantage6-server and the client.

**F**

-  **FAIR data**: data that are Findable, Accessible, Interoperable, and
   Reusable. For more information, see `the original
   paper <https://www.nature.com/articles/sdata201618.pdf?origin=ppub>`__.
-  **Federated Analytics**: an approach for analyzing data that are
   spread across different parties using traditional statistical methods. The main
   idea is that parties run computations on their local data, yielding aggregated
   parameters. These are then shared to generate a global (statistical) model.
-  **Federated learning**: an approach for analyzing data that are
   spread across different parties using machine learning methods. The main
   idea is that parties run computations on their local data, yielding
   aggregated parameters. These are then shared to generate a global (statistical)
   model.
-  **Federated function**: A function that is executed on the local data of a party.
   It is a part of a *federated Analytics* or *federated learning* algorithm.

**H**

-  **Heterogeneity**: the condition in which in a federated learning scenario, parties
   are allowed to have differences in hardware and software (i.e., operating systems).
-  **Horizontally-partitioned data**: data spread across different parties where the
   latter have the same features of different instances (i.e., patients). See also
   vertically-partitioned data.

.. figure:: /images/horizontal_partition.png
   :alt: Horizontally partitioned data
   :align: center

   Horizontally-partitioned data

-  **Horizontal scaling**: the ability of a system to handle an increasing amount of
   requests by creating more instances of itself.

**I**

- **Image**: A blueprint for a *container*, which can be stored in a *Docker registry*.

**J**

-  **JWT Token**: A JSON Web Token used for authentication and authorization in the
   system.

**K**

- **Kubernetes**: An open-source system for automating deployment, scaling, and
   operations of application containers across clusters of hosts. In vantage6 it is the
   fundamental technology that is used to run the vantage6-server and nodes.

**N**

-  **Node**: vantage6 node application that runs at a **Data Station** which has access
   to the local data.

**M**

-  **Multi-party computation**: an approach to perform analyses across
   different parties by performing operations on encrypted data.

**P**

-  **Partial function**: The federated part of an algorithm that runs on local data
   at nodes.
-  **Party**: an entity that takes part in one (or more) collaborations, in vantage6
   a party is an organization.
-  **Permission scope**: The level of access granted to users for viewing and modifying
   dataframes (personal, organization, or collaboration level).
-  **Pre-processing task**: A task that modifies dataframes by adding or removing
   columns, or filtering rows.
-  **Privacy-enhancing Technology (PET)**: Technologies that enable privacy-preserving
   analyses on federated data. This includes technologies such as differential
   privacy, secure multi-party computation, and federated analytics/learning.
-  **Python**: a high-level general purpose programming language. It
   aims to help programmers write clear, logical code. vantage6 is
   `written in Python <https://github.com/vantage6/vantage6>`__.

**R**

-  **RSA keys**: Cryptographic keys used for encryption and decryption of data between
   organizations.

**S**

-  **Secure multi-party computation**: see *Multi-party computation*
-  **Server**: Public access point of the vantage6 infrastructure. Contains at
   least the **vantage6-server** application but can also host the optional
   components: Docker registry, VPN server and RabbitMQ. In this documentation
   space we try to be explicit when we talk about *server* and
   *vantage6 server*, however you might encounter *server* where
   *vantage6 server* should have been.
-  **Session**: A way to prepare a dataset that can be re-used in many computation
   tasks, especially useful for large datasets and flexible pre-processing.
-  **Study**: A study is a sub-group of organizations within a collaboration.

**T**

-  **Task**: A task is a request from a client to the vantage6-server to execute an
   algorithm. Is is the main unit of work in vantage6.
-  **TOTP (Time-based One-Time Password)**: A form of two-factor authentication where
   users generate time-based codes using an authenticator app.
-  **Two-factor authentication**: A method of authentication that requires two
   forms of identification.


**V**

-  **vantage6**: priVAcy preserviNg federaTed leArninG infrastructurE
   for Secure Insight eXchange. In short, vantage6 is an infrastructure
   for executing federated learning analyses. However, it can also be
   used as a FAIR data station and as a model repository.
-  **Vertically-partitioned data**: data spread across different parties
   where the latter have different features of the same instances (i.e.,
   patients). See also horizontally-partitioned data.

.. figure:: /images/vertical_partition.png
   :alt: Vertically partitioned data
   :align: center

   Vertically partitioned data

**W**

-  **Wrapper**: A library that simplifies and standardizes the interaction between the
   node and algorithm container, handling data reading and writing operations.
-  **Whitelist**: A list of allowed domains, ports, and IP addresses that algorithms
   can access.

.. todo Add references to sections of the docs where to find info on them