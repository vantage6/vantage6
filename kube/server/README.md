# Kubernetes Deployment for Vantage6 Server
I needed to install the ingress controller for my Kubernetes cluster. I used the
following command to install the ingress controller:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

Then I could deploy the Vantage6 server using the following command:
```bash
kubectl apply -f kube/server/namespaces.yaml
kubectl apply -f kube/server/.
```

> **⚠ Important**
> * This deployment does not contain any SSL certificates. You still need to setup cert-manager and configure the ingress to use the certificates.
> * `replicas` is set to 1 in the deployment files. You are free to change this to
> a higher number if you want to run multiple instances of the server.
>    * **However** you need to make sure to enable the `sessionAffinity: ClientIP` in the *backend* and *store* file!
>    * First start the server with `replicas: 1` to populate the database. Then you can scale up the server to multiple instances.

## Deployment Overview
The deployment consists of the following components:

- **vantage6-server**: The vantage6 server instance, connection point for users and
                       nodes.
  - **database**: The database for the server. This is a PostgreSQL database.
  - **rabbitmq**: The message broker for the server. This is a RabbitMQ instance.

- **vantage6-frontend**: The vantage6 frontend instance, the user interface for the
                         server and store
- **vantage6-store**: The vantage6 store instance, the store for algorithms to be used
                      on the vantage6 network.

More details about these components can be found
[here](https://docs.vantage6.ai/en/main/introduction/architecture.html).

## Configuration

```text
The following services are deployed in the Kubernetes cluster:

                            SERVICES
                  ┌─────────────────────────────────────────────────────┐
                  │                                                     │
 ┌────────────┐   │  ┌───────────────┐             ┌─────────────┐      │
 │            │   │  │               │             │             │      │
 │  Ingress   ┼─┬─┼──►  vantage6 UI  │         ┌───►  Server DB  │      │
 │            │ │ │  │  (/)          │         │   │             │      │
 └────────────┘ │ │  └───┬──────────┬┘         │   └─────────────┘      │
                │ │      │          │          │                        │
                │ │      │          │          │                        │
                │ │   ┌──▼──────────┴──────┐   │   ┌─────────────┐      │
                │ │   │                    │   │   │             │      │
                ┼─┼───►  vantage6 server   ┼───┴───►  RabbitMQ   │      │
                │ │   │  (/api)            │       │             │      │
                │ │   └───────────┬────────┘       └─────────────┘      │
                │ │               │                                     │
                │ │               │                                     │
                │ │           ┌───▼──────┐         ┌─────────────┐      │
                │ │           │          │         │             │      │
                └─┼───────────►  Store   ┼─────────►  Store DB   │      │
                  │           │  (/store)│         │             │      │
                  │           └──────────┘         └─────────────┘      │
                  │                                                     │
                  └─────────────────────────────────────────────────────┘
```

