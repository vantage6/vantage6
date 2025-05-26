import { Injectable, inject, effect } from '@angular/core';
import Keycloak from 'keycloak-js';
import { KEYCLOAK_EVENT_SIGNAL, KeycloakEventType, typeEventArgs, ReadyArgs } from 'keycloak-angular';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  authenticated = false;
  authenticated$ = new BehaviorSubject<boolean>(false);
  keycloakStatus: string | undefined;
  private readonly keycloak = inject(Keycloak);
  private readonly keycloakSignal = inject(KEYCLOAK_EVENT_SIGNAL);

  constructor() {
    effect(() => {
      const keycloakEvent = this.keycloakSignal();

      this.keycloakStatus = keycloakEvent.type;

      if (keycloakEvent.type === KeycloakEventType.Ready) {
        this.authenticated = typeEventArgs<ReadyArgs>(keycloakEvent.args);
        this.authenticated$.next(this.authenticated);
      }

      if (keycloakEvent.type === KeycloakEventType.AuthLogout) {
        this.authenticated = false;
        this.authenticated$.next(this.authenticated);
      }
    });
  }

  getToken(): string | undefined {
    return this.keycloak.token;
  }

  authenticatedObservable(): Observable<boolean> {
    return this.authenticated$.asObservable();
  }

  async login(): Promise<void> {
    this.keycloak.login();
  }

  logout(): void {
    this.keycloak.logout();
  }
}
