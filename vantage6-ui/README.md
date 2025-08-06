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

This part of the repository contains the code for our User Interface.
This is a web application that allows you to communicate easily with your **vantage6** server.

## How to use

For instructions on how to run your own user interface, see the instructions below.
If you are using our Cotopaxi server you can use this user interface by logging
on to https://portal.cotopaxi.vantage6.ai/. Contact us if you would like to have
a user account.

### Running the UI locally

The easiest way to run the UI locally is using the ``--with-ui`` flag in the
``v6 server start`` command. That will automatically start a UI container, by default
on port 7600.

Alternatively, you can run the UI natively in [Angular](https://github.com/angular/angular-cli).
For general information on how to work with Angular, we refer to
the [Angular CLI home page](https://angular.io/cli). You may need to install these
[requirements](https://angular.io/guide/setup-local) to run Angular
applications locally.

Before running the application, you may need to update the configuration. Update
the file in `src/environments/environment.development.ts` to set where your vantage6
server is running (or, alternatively, update `environment.ts` if you want to run a
production application).

When you have completed the steps above, run

```
ng serve
```

for a development server. Navigate to `http://localhost:4200/` to use it.

### Deployment

Angular production servers can be deployed in many ways. Angular's
[deployment documentation](https://angular.io/guide/deployment) offers a number
of options.

Alternatively, we provide the Docker image `harbor2.vantage6.ai/infrastructure/ui`
to help you deploy your own UI. In that case, run

```
docker run --env SERVER_URL="<your_url>" --env API_PATH="<your_path>" -p 8080:80 harbor2.vantage6.ai/infrastructure/ui:latest
```

to run a UI on port 8080 that communicates with your own server. For instance,
you can point to a local server with default settings if you set
SERVER_URL=`http://localhost:7601` and API_PATH=`/api`.
If you don't enter environment variables, the UI points to
`https://cotopaxi.vantage6.ai` by default.

Note that you can also use another UI image tag than `ui:latest`. For example,
you can specify a version of the UI such as `ui:4.3.0`. Another option is
to use the tag `ui:cotopaxi`, which defaults to the latest v4 version.

#### Security settings

Finally, there is also an environment variable `ALLOWED_ALGORITHM_STORES` that
you can specify. If you do so, the appropriate
[CSP headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP) will be
set so that your UI can only access the vantage6 server and algorithm stores
to collect data from. You define them same as other environment variables, with
spaces in between each algorithm store you want to allow traffic from:

```
docker run --env ALLOWED_ALGORITHM_STORES="store.cotopaxi.vantage6.ai myotherstore.com" ...
```

Note that if you do _not_ specify this environment variable, the CSP policy
will be very lenient. In order for the UI to work properly, algorithm store
resources should be obtained, so if no algorithm stores are provided, the CSP policies
will be very lenient.
