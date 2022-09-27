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
of options. Alternatively, you can use the Docker image we have made available on
[harbor2.vantage6.ai/infrastructure/ui](harbor2.vantage6.ai/infrastructure/ui)
to deploy you own UI.
