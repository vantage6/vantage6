import { Injectable, inject, effect } from '@angular/core';
import Keycloak from 'keycloak-js';
import { KEYCLOAK_EVENT_SIGNAL, KeycloakEventType, typeEventArgs, ReadyArgs } from 'keycloak-angular';
import { BehaviorSubject, Observable } from 'rxjs';
import { AuthRedirectService } from './auth-redirect.service';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  authenticated = false;
  authenticated$ = new BehaviorSubject<boolean>(false);
  keycloakStatus: string | undefined;
  private readonly keycloak = inject(Keycloak);
  private readonly keycloakSignal = inject(KEYCLOAK_EVENT_SIGNAL);
  private readonly authRedirectService = inject(AuthRedirectService);

  constructor() {
    effect(() => {
      const keycloakEvent = this.keycloakSignal();

      this.keycloakStatus = keycloakEvent.type;

      if (keycloakEvent.type === KeycloakEventType.Ready) {
        this.authenticated = typeEventArgs<ReadyArgs>(keycloakEvent.args);
        this.authenticated$.next(this.authenticated);

        // Check if there's a stored intended URL and redirect to it
        if (this.authenticated && this.authRedirectService.hasIntendedUrl()) {
          const intendedUrl = this.authRedirectService.getAndClearIntendedUrl();
          const currentUrl = window.location.pathname + window.location.search + window.location.hash;
          if (intendedUrl && currentUrl !== intendedUrl) {
            // small timeout to ensure the page is fully loaded
            setTimeout(() => {
              window.location.href = intendedUrl;
            }, 100);
          }
        }
      }

      if (keycloakEvent.type === KeycloakEventType.AuthLogout) {
        this.authenticated = false;
        this.authenticated$.next(this.authenticated);
      }

      // Handle token expiration
      if (keycloakEvent.type === KeycloakEventType.TokenExpired) {
        const currentUrl = window.location.pathname + window.location.search + window.location.hash;
        this.authRedirectService.setIntendedUrl(currentUrl);
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
