.. _hub-admin-guide-prometheus:

Prometheus
==========

The `Prometheus <https://prometheus.io/>`_ component is responsible for collecting
metrics from the vantage6 nodes. The node collects metrics such as CPU usage, memory
usage, system load, etc., and sends them to vantage6 HQ over the
:ref:`socket <socket>` connection. At vantage6 HQ, a Prometheus exporter is running
that exposes the metrics to Prometheus.

How to use
----------

To use Prometheus, you only need to configure vantage6 HQ and the nodes correctly.

You can configure the server correctly by configuring the ``prometheus`` section of the
HQ configuration file. An example is included in the HQ configuration file
:ref:`here <hq-configuration-file>`. When this is configured correctly, an HQ deployment
will automatically start a Prometheus server that scrapes the metrics from the nodes.

The nodes then need to be configured such that they allow sending metrics to HQ. To
enable this, check out the ``prometheus`` section of the
:ref:`node configuration file <node-configure-structure>`. It is not problematic if only
part of the nodes allow sending metrics to HQ - then you will simply see the metrics
for fewer nodes.
