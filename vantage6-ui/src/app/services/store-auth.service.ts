import { Injectable } from '@angular/core';
import Keycloak from 'keycloak-js';
import { environment } from 'src/environments/environment';

/*
 * Provides the token for algorithm stores.
 *
 * Algorithm stores get a separate token from a separate Keycloak client, which HQ does
 * not accept. The user is already logged in to Keycloak, so this logs in silently.
 */
@Injectable({
  providedIn: 'root'
})
export class StoreAuthService {
  private readonly keycloak = new Keycloak({
    realm: environment.keycloak_realm,
    url: environment.auth_url,
    clientId: environment.keycloak_store_client
  });
  private initialized: Promise<boolean> | null = null;

  async getToken(): Promise<string | undefined> {
    if (!this.initialized) {
      this.initialized = this.keycloak
        .init({
          onLoad: 'check-sso',
          silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html'
        })
        .catch(() => false);
    }
    if (!(await this.initialized)) {
      return undefined;
    }
    try {
      await this.keycloak.updateToken(30);
    } catch {
      return undefined;
    }
    return this.keycloak.token;
  }
}
