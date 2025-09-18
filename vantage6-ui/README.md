<h1 align="center">
  <br>
  <a href="https://vantage6.ai"><img src="https://github.com/IKNL/guidelines/blob/master/resources/logos/vantage6.png?raw=true" alt="vantage6" width="350"></a>
</h1>

<h3 align=center> A privacy preserving federated learning solution</h3>

<p align="center">
  <a href="#books-documentation">Documentation</a> •
  <a href="#gift_heart-contributing">Contributing</a> •
  <a href="#black_nib-references">References</a>
</p>

---

This part of the repository contains the code for the vantage6 user interface
(UI). This is a web application that allows you to communicate easily with
your vantage6 server.

## How to use

For instructions on how to run your own user interface, see the instructions below.
If you are using our Cotopaxi server you can use this user interface by logging
on to https://portal.cotopaxi.vantage6.ai/. Contact us if you would like to have
a user account.

### Running the UI locally

The UI is started locally with the ``v6 server start`` command. It will also be
included in a sandbox environment that can be started with
``v6 sandbox start``. Both commands will automatically start a user interface
on `http://localhost:7600`. Port 7600 is the default: it is possible to configure
running it on another port by changing the configuration file.

For developers, it is recommended to use ``v6 dev`` commands. Local code changes are
then synced to the UI deployment. This UI deployment is also available on
`http://localhost:7600`.

### Deployment

There are several ways in which you may deploy the UI. The most convenient way is
to use the CLI:

```
v6 server start
```

This command starts up the UI together with the vantage6 server.

Alternatively. Angular's
[deployment documentation](https://angular.io/guide/deployment)
offers a number of options to deploy the UI code directly without container
technology.

Finally, note that kubernetes uses the Docker image
`harbor2.vantage6.ai/infrastructure/ui` to run the UI. One could also run the UI
with a command such as:

```
docker run --env SERVER_URL="<your_url>" --env API_PATH="<your_path>" \
  -p 8080:80 harbor2.vantage6.ai/infrastructure/ui:latest
```

This is recommended for v4 deployments, but no longer in v5. Please checkout
this README in a `release/4.x` branch (e.g. release/4.13) to view more details.

#### Security settings

The appropriate [CSP headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
will be generated when you deploy the UI through the kubernetes interface.
The CSP headers are set so that your UI can only access the vantage6 server and
algorithm stores.

Note that it is important that the UI has settings on the allowed algorithm
stores to set a proper security policy. If the UI allows all algorithm store,
the CSP policy will be very lenient, because it will allow connecting to any
URL to facilitate connecting to any algorithm store.