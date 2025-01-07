# Kubernetes Deployment for Vantage6 Server
I needed to install the ingress controller for my Kubernetes cluster. I used the following command to install the ingress controller.

- [ ] write documentation
- [x] add RabbitMQ service
- [x] make sessions to the server sticky
- [ ] add algorithm store service
- [ ] use secrets for sensitive data
- [x] add persistent storage for the database
- [x] Add namespace for all resources

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

```bash
kubectl apply -f kube/server/.
```

This YAML file defines the deployment and service configurations for the Vantage6
server backend and frontend components. The architecture includes a LoadBalancer for
external access, an Ingress Controller for routing, and separate services for the
backend and frontend.

Architecture Overview:
+-------------------+       +---------------------+       +-------------------+
|   LoadBalancer    |------>|      Ingress        |------>|   Backend Service |
| (External Access) |       | (Ingress Controller)|       |  Frontend Service |
+-------------------+       +---------------------+       +-------------------+

The LoadBalancer exposes the Ingress Controller to external traffic. The Ingress
Controller manages routing rules and directs traffic to the appropriate service based
on the request path or host. The backend and frontend services route traffic to their
respective pods.

Backend Service: Handles the server-side logic and API endpoints.
Frontend Service: Handles the client-side application and user interface.

This configuration ensures that the Vantage6 server components are properly deployed,
exposed, and accessible within the Kubernetes cluster.


