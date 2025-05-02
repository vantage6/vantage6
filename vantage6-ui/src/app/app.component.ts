import { Component, inject, effect } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { RouterOutlet } from '@angular/router';
import { KEYCLOAK_EVENT_SIGNAL, KeycloakEventType } from 'keycloak-angular';
import { Router } from '@angular/router';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  imports: [RouterOutlet]
})
export class AppComponent {
  private readonly keycloakSignal = inject(KEYCLOAK_EVENT_SIGNAL);

  constructor(translate: TranslateService, private router: Router) {
    translate.setDefaultLang('en');
    translate.use('en');

    effect(async () => {
      if (this.keycloakSignal().type === KeycloakEventType.AuthRefreshError) {
        await this.router.navigate(['/', 'logout']);
      }
    });
  }
}


