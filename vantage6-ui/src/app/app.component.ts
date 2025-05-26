import { Component, inject, effect } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { RouterOutlet } from '@angular/router';
import { KEYCLOAK_EVENT_SIGNAL, KeycloakEventType } from 'keycloak-angular';
import { Router } from '@angular/router';
import { OnLoginStatusChangeService } from './services/on-login-status-change.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  imports: [RouterOutlet]
})
export class AppComponent {
  private readonly keycloakSignal = inject(KEYCLOAK_EVENT_SIGNAL);

  constructor(
    translate: TranslateService,
    // TODO this import is here to ensure that the service is initialized and used.
    // It should be imported in the app.config.ts file instead.
    private onLoginStatusChangeService: OnLoginStatusChangeService,
    private router: Router
  ) {
    translate.setDefaultLang('en');
    translate.use('en');

    effect(async () => {
      if (this.keycloakSignal().type === KeycloakEventType.AuthRefreshError) {
        await this.router.navigate(['/', 'logout']);
      }
    });
  }
}
