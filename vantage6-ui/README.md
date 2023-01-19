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

This repository is part of **vantage6**, and contains the code for our User Interface.
This is a web application that allows you to communicate easily with your **vantage6** server.

## How to use

For instructions on how to run your own user interface, see the instructions below.

If you are using our Petronas server you can use this user interface by logging
on to https://portal.petronas.vantage6.ai/. Contact us if you would like to have
a user account.

Note that the user interface is not available for older **vantage6** servers
such as Harukas. Please consider upgrading your project to Petronas.

### Running the UI

This UI is an [Angular](https://github.com/angular/angular-cli) (version 14.1.3)
application. For general information on how to work with Angular, we refer to
the [Angular CLI home page](https://angular.io/cli). You may need to install these
[requirements](https://angular.io/guide/setup-local) to run Angular
applications locally.

Before running the application, you may need to update the configuration. Update
the file in `src/environments/environment.ts` to set where your vantage6 server
is running (or, alternatively, update `environment.prod.ts` if you want to run a
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
SERVER_URL=`http://localhost:5000` and API_PATH=`/api`.
If you don't enter environment variables, the UI points to
`https://petronas.vantage6.ai` by default.

Note that you can also use another UI image tag than `ui:latest`. For example,
you can specify a version of the UI such as `ui:3.6.0`. Another option is
to use the tag `ui:petronas`, which defaults to the latest v3 version.
